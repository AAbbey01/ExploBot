from flask import Flask, request
import os
import requests
import re
import gspread
import config
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Your GroupMe bot token
BOT_ID = config.BOT_ID  
GROUP_ID = config.GROUP_ID
BOT_TOKEN = config.BOT_TOKEN
# Dictionary to track points for each user who spots someone
user_points = {}

# Set up Google Sheets integration
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(config.CRED_FILE, scope)  
client = gspread.authorize(creds)
sheet = client.open(config.SPREADSHEET_NAME).sheet1  

# Function to send messages to GroupMe
def send_message(text):
    url = 'https://api.groupme.com/v3/bots/post'
    data = {
        'bot_id': BOT_ID,
        'text': text
    }
    requests.post(url, json=data)

# Function to check if the coordinates are within a specific area (bounding box example)
def is_within_area(latitude, longitude, area_bounds):
    lat_min, lat_max, long_min, long_max = area_bounds
    print(lat_min <= latitude <= lat_max and long_min <= longitude <= long_max)
    return lat_min <= latitude <= lat_max and long_min <= longitude <= long_max

# Function to detect "Spotted" followed by coordinates and handle mentions
def check_for_spotted_and_coords(text, attachments):
    mentioned_user = None
    for attachment in attachments:
        print(attachment)
        if attachment['type'] == 'mentions':
            user_ids = attachment['user_ids']
            mentioned_user = user_ids[0] if user_ids else None
    if mentioned_user:
        pattern = r"(spotted)*\s*\(\s*(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)\s*\)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            latitude = float(match.group(1))
            longitude = float(match.group(2))
            return mentioned_user, latitude, longitude
    return None, None, None

# Function to send a success message after a spot, based on spreadsheet data
def send_spot_success_message(spotter_name, spotted_name):
    # Retrieve updated data for spotter and spotted person
    spotter_row = find_user_row(spotter_name)
    spotted_row = find_user_row(spotted_name)

    if spotter_row:
        spotter_spots = int(sheet.cell(spotter_row, 4).value)  # Times_Spotted (Column 2)
    else:
   #     send_message("failed to find spotter")
        return
    if spotted_row:
        spotted_been_spotted = int(sheet.cell(spotted_row, 5).value)  # Times_Been_Spotted (Column 3)
    else:
    #    send_message("failed to get who has been spotted")
        return

    # Generate and send the success message
    spotter_name_from_id = get_nickname_from_id(spotter_name)
    spotted_name_from_id = get_nickname_from_id(spotted_name)
    success_message = (
        f"{spotter_name_from_id} successfully spotted {get_nickname_from_id(spotted_name)}! "
        f"{spotter_name_from_id} has now spotted {spotter_spots} {"people" if spotter_spots >1 else "person"} this week, and "
        f"{spotted_name_from_id} has been spotted {spotted_been_spotted} {"time" if spotted_been_spotted == 1 else "times"} this week."
    )
    send_message(success_message)


# Function to log the spot data in the Google Sheet
def log_spot_in_sheet(spotter_id, spotted_id):
    spotter_row = find_user_row(spotter_id)
    spotted_row = find_user_row(spotted_id)
    
    # Weekly Tracker (Columns D and E)
    if spotter_row is None:
        sheet.append_row([spotter_id, 0, 0, 1, 0])
    else:
        current_weekly_spots = int(sheet.cell(spotter_row, 4).value)
        sheet.update_cell(spotter_row, 4, current_weekly_spots + 1)

    if spotted_row is None:
        sheet.append_row([spotted_id, 0, 0, 0, 1])
    else:
        current_weekly_been_spotted = int(sheet.cell(spotted_row, 5).value)
        sheet.update_cell(spotted_row, 5, current_weekly_been_spotted + 1)

# Helper function to find a user's row in the Google Sheet
def find_user_row(user_name):
    try:
        # Get all values in the first column (user names)
        cell = sheet.find(user_name)
        if cell:
            print(f"User {user_name} found at row {cell.row}")
            return cell.row
    except:
        print(f"User {user_name} not found, adding new row.")
        # Append a new row for the user if they are not found
        sheet.append_row([user_name, 0, 0,0,0])  # User has spotted 0 people and been spotted 0 times
        new_row = len(sheet.get_all_values())  # Get the last row number
        print(f"New user {user_name} added at row {new_row}")
        return new_row

def get_group_members():
    url = f"https://api.groupme.com/v3/groups/{GROUP_ID}?token={BOT_TOKEN}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        group_data = response.json()
        members = group_data['response']['members']
        
        # Create a dictionary of {user_id: nickname}
        user_dict = {member['user_id']: member['nickname'] for member in members}
        
        return user_dict
    else:
        print(f"Error fetching group members: {response.status_code}")
        return None

# Function to translate user ID to nickname
def get_nickname_from_id(user_id):
    user_dict = get_group_members()  # Get the user dictionary
    
    if user_dict and user_id in user_dict:
        return user_dict[user_id]
    else:
        return "Unknown User"



@app.route('/')
def hello():
    return "Hi"

# Webhook endpoint that GroupMe will hit
@app.route('/groupme', methods=['POST'])
def webhook():
    data = request.get_json()

    # Ignore messages from the bot itself
    if data['sender_type'] == 'bot':
        return "OK", 200

    # Extract the message text and attachments
    text = data.get('text', '')
    attachments = data.get('attachments', [])
    
    # Check for the word "Spotted" and coordinates with a mention
    mentioned_user, latitude, longitude = check_for_spotted_and_coords(text, attachments)
    
    if mentioned_user and latitude and longitude:
        # Check if coordinates are within a specific area (e.g., a campus)
        area_bounds = (config.lat_min, config.lat_max, config.long_min, config.long_max)  # Example bounds (min lat, max lat, min long, max long)
        if is_within_area(latitude, longitude, area_bounds):
            sender_id = data['sender_id']
            sender_name = data['name']  # Name of the user who sent the message

            # Get the name of the user who was mentioned (@user)
            mentioned_user_name = None
            for attachment in attachments:
                if attachment['type'] == 'mentions':
                    mentioned_user_name = attachment['user_ids'][0]  # Mentioned user's name
            print(mentioned_user_name)
            # Log the spotting in Google Sheets
            if mentioned_user_name:
                log_spot_in_sheet(sender_id, mentioned_user_name)
                print(sender_id)

            # Send success message with updated stats
            send_spot_success_message(sender_id, mentioned_user_name)
        #else:
             #send_message(f"Coordinates are outside the designated area.")
    else:
        return "OK", 200


def send_startup_message():
    url = 'https://api.groupme.com/v3/bots/post'
    data = {
        'bot_id': BOT_ID,
        'text': 'Bot has started and is now connected!'
    }
    response = requests.post(url, json=data)
    if response.status_code != 202:
        print(f"Failed to send startup message: {response.status_code}")


if __name__ == "__main__":
    #send_startup_message()
    print("Started!!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


