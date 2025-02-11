# ExploBot V1.0.1 Is here!!!
This version is the official used version by Explorchestra.

## Features
- Automatically Reads messages from GroupMe
- Determines via Regex if data is valid for the Spotting Game
- Automatically adds correct 'spots' into a Google Spreadsheet
- Defines an endpoint to see the leaderboard
- Continuously Deploys via Google Cloud Console (Google Run

## Dependencies
### config.py
- Gives a place to specify API keys, bounds for the game, and spreadsheet credentials
### patterns.py
- Specifies regex patterns for Google Maps, Apple Maps, and iOS Compass application's coordinate systems
- Defines functions to confirm and extract coordinates
### requirements.txt
- Specifies imports for the Dockerfile, which is used for Gcloud to build and deploy the app
