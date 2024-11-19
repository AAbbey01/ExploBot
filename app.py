from flask import Flask, request, render_template
import os
import requests
import re
import gspread
import config
from oauth2client.service_account import ServiceAccountCredentials
import time
import google.cloud.logging
import logging
import patterns

# Instantiates a client
client = google.cloud.logging.Client()
client.setup_logging()

app = Flask(__name__)

# Your GroupMe bot token
BOT_ID = config.BOT_ID  
GROUP_ID = config.GROUP_ID
BOT_TOKEN = config.BOT_TOKEN

# Dictionary to track users in groupMe group on startup
user_points = {}

# Set up Google Sheets integration
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(config.CRED_FILE, scope)  
client = gspread.authorize(creds)
sheet = client.open(config.SPREADSHEET_NAME).sheet1  

# Function to check if the coordinates are within a specific area (bounding box example)
def is_within_area(latitude, longitude, area_bounds):
    lat_min, lat_max, long_min, long_max = area_bounds
    return lat_min <= latitude <= lat_max and long_min <= longitude <= long_max

# Function to detect "Spotted" followed by coordinates and handle mentions
def check_for_spotted_and_coords(text, attachments):
    mentioned_user = None
    for attachment in attachments:
        if attachment['type'] == 'mentions':
            user_ids = attachment['user_ids']
            mentioned_user = user_ids[0] if user_ids else None
    if mentioned_user:
        for i in patterns.pattern_types:
            if re.search(i,text,re.IGNORECASE):
                logging.debug(f"Spotted with {patterns.map_types[patterns.pattern_types.index(i)]}")
                return mentioned_user, patterns.func_types[patterns.pattern_types.index(i)](re.search(i,text,re.IGNORECASE))
        logging.warning(f"Couldnt find coordinates with data given:\n didnt find {mentioned_user}, with text {text}")
        return mentioned_user, (None, None)
    #no mentioned user means dont care
    else:
        logging.warning("No real mentioned User")
        return None, (None, None)

# Function to log the spot data in the Google Sheet
def log_spot_in_sheet(spotter_id, spotted_id, message_id):
    spotter_row = find_user_row(spotter_id)
    spotted_row = find_user_row(spotted_id)
    # Weekly Tracker (Columns D and E)
    if spotter_row is None:
        sheet.append_row([spotter_id, 0, 0, 1, 0, get_nickname_from_id(spotter_id)])
    else:
        current_weekly_spots = int(sheet.cell(spotter_row, 4).value) if int(sheet.cell(spotter_row, 4).value) is not None else 0
        sheet.update_cell(spotter_row, 4, current_weekly_spots + 1)
    if spotted_row is None:
        sheet.append_row([spotted_id, 0, 0, 0, 1,get_nickname_from_id(spotted_id)])
    else:
        current_weekly_been_spotted = int(sheet.cell(spotted_row, 5).value) if int(sheet.cell(spotted_row, 5).value) is not None else 0
        sheet.update_cell(spotted_row, 5, current_weekly_been_spotted + 1)
    url = f'https://api.groupme.com/v3/messages/{GROUP_ID}/{message_id}/like?token={BOT_TOKEN}'
    response = requests.post(url)
    if response.status_code == 200:
        return "OK",200
    else:
        return "Err", 400

# Helper function to find a user's row in the Google Sheet
def find_user_row(user_name):
    try:
        # Get all values in the first column (user names)
        cell = sheet.find(user_name)
        if cell:
            logging.warning(f"User {user_name} found at row {cell.row}")
            return cell.row
    except:
        logging.warning(f"User {user_name} not found, adding new row.")
        # Append a new row for the user if they are not found
        sheet.append_row([user_name, 0, 0,0,0])  # User has spotted 0 people and been spotted 0 times
        new_row = len(sheet.get_all_values())  # Get the last row number
        logging.warning(f"New user {user_name} added at row {new_row}")
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
        logging.error(f"Error fetching group members: {response.status_code}")
        return None

# Function to translate user ID to nickname
def get_nickname_from_id(user_id):
    user_dict = get_group_members()  # Get the user dictionary
    
    if user_dict and user_id in user_dict:
        return user_dict[user_id]
    else:
        return "Unknown User"

#Leaderboard Endpoint, Want to make it better
@app.route('/leaderboard',methods=['GET'])
def display_leaderboard():
    data = sheet.get_all_values()
    for row in data: 
        row[0] = get_nickname_from_id(row[0])
    data = [row[:3] for row in data]
    return render_template('table.html',data=data)

#Base Path, Eventually Populate with more than just "Hi"
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
    message_id = data['id'];
    logging.debug(f"message id: {message_id}")
    # Extract the message text and attachments
    text = data.get('text', '')
    attachments = data.get('attachments', [])
    logging.info(text)
    # Check for the word "Spotted" and coordinates with a mention
    
    mentioned_user, (latitude, longitude) = check_for_spotted_and_coords(text, attachments)
    sender_id = data['sender_id']
    if mentioned_user and latitude and longitude:
        if(longitude >0):
            longitude = -1 * longitude
        # Check if coordinates are within a specific area (e.g., a campus)
        area_bounds = (config.lat_min, config.lat_max, config.long_min, config.long_max)  # Example bounds (min lat, max lat, min long, max long)
        if is_within_area(latitude, longitude, area_bounds):
            
            sender_name = data['name']  # Name of the user who sent the message

            # Get the name of the user who was mentioned (@user)
            mentioned_user_names = {}
            mentioned_user_name = None
            for attachment in attachments:
                if attachment['type'] == 'mentions':
                    mentioned_user_name = attachment['user_ids'][0]  # Mentioned user's name
                    mentioned_user_names = attachment['user_ids']
                    logging.info(f"All mentioned users in chat = {mentioned_user_names}")
            
            # Log the spotting in Google Sheets
            if len(mentioned_user_names)>0:
                _ = [log_spot_in_sheet(sender_id,sing_mentioned_user, message_id) for sing_mentioned_user in mentioned_user_names]
            
            elif mentioned_user_name:
                log_spot_in_sheet(sender_id, mentioned_user_name, message_id)
        else:
            logging.warning(f"Coordinates are outside the designated area for {mentioned_user} at {latitude} and {longitude}\n the message came from {get_nickname_from_id(sender_id)}")
    else:
        logging.warning(f"Could not find {mentioned_user} at {latitude} and {longitude}")
    return "OK", 200

#Start Log, Ensure the connection occurs
def startup_log():
    url = 'https://api.groupme.com/v3/bots/post'
    data = {
        'bot_id': BOT_ID,
        'text': 'Bot has started and is now connected!'
    }
    logging.debug(f"Bot Operational as of {time.ctime(time.time())}")

#Main
if __name__ == "__main__":
    startup_log()

    if get_group_members():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        logging.error("Auth Failure")