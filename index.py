from openai import OpenAI
from dotenv import load_dotenv
import requests
import os
import re
import json
import random

load_dotenv()

# Set the Spotify playlist ID
playlist_id = "4OGL14XW0rPSnLy71pWQE5"

# Initialize the OpenAI client with your API key
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')


# Spotify access token request
def get_access_token(client_id, client_secret):
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        return access_token
    else:
        print("Failed to retrieve token. Status code:", response.status_code)
        print("Response:", response.json())
        return None

# Playlist Spotify request
def get_playlist_data(access_token, playlist_id):
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}?fields=tracks.items(track(name,artists(name),album(name)))'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        playlist_data = response.json()
        return playlist_data
    else:
        print("Failed to retrieve playlist data. Status code:", response.status_code)
        print("Response:", response.json())
        return None

# Get the access token and playlist data from Spotify
access_token = get_access_token(client_id, client_secret)
playlist_songs = []

if access_token:
    playlist_data = get_playlist_data(access_token, playlist_id)
    if playlist_data:
        songs = playlist_data["tracks"]["items"]
        random.shuffle(songs)  # Shuffle the songs
        playlist_songs = songs[:25]
        playlist_songs = json.dumps(playlist_songs).replace('"', '\\"')
        print(playlist_songs)

# Create the assistant
assistant = client.beta.assistants.create(
    name="Music Suggestions",
    instructions="You are an expert music analyst. Use your knowledge base to answer questions about which song fits more for me. Also just answer only with the song name and song artists for each song you recommend, you should not write anything else just the songs. example: 1. Song Name - Artist Name",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
)
#Function to parse response
def parse_value(text):
    # Use regular expression to find 'value=' and extract the value that follows
    match = re.search(r"value='([^']*)'", text)
    if match:
        return match.group(1)
    else:
        return None

# Function to verify file existence and readability
def verify_file(file_paths):
    for path in file_paths:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File {path} not found.")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"File {path} cannot be read.")

# List of JSON file paths to upload
file_paths = [
    "datasets/dataset1.json",
    "datasets/dataset2.json",
    "datasets/dataset3.json",
    "datasets/dataset4.json",
    "datasets/dataset5.json",
    "datasets/dataset6.json"
]

# Verify files before uploading
try:
    verify_file(file_paths)
except Exception as e:
    print(f"File verification failed: {e}")
    exit(1)

# Upload the user-provided files to OpenAI
uploaded_files = []
for file_path in file_paths:
    try:
        message_file = client.files.create(
            file=open(file_path, "rb"), purpose="assistants"
        )
        uploaded_files.append(message_file.id)
    except Exception as e:
        print(f"Failed to upload file {file_path}: {e}")

if not uploaded_files:
    print("No files were uploaded successfully.")
    exit(1)

# Create a thread and attach the files to the message
try:
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"Search for the following songs in the database: \n{playlist_songs} For each matched song, look for its “popularity”, “duration_ms”, “explicit”, “danceability”, “energy”, “key”, “loudness”, “mode”, “speechiness”, “acousticness”, “instrumentalness”, “liveness”, “valence”, “tempo”, “time_signature”, and “track_genre” details. Based on these songs and their attributes, identify 5 similar songs from the database that I may like and provide only the name an artist of each song.",
                "attachments": [{"file_id": file_id, "tools": [{"type": "file_search"}]} for file_id in uploaded_files]
            }
        ]
    )
except Exception as e:
    print(f"Failed to create thread: {e}")
    exit(1)

# Use the create and poll SDK helper to create a run and poll the status of
# the run until it's in a terminal state.
try:
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
    message_content = messages[0].content[0].text

    message_content = parse_value(f"{message_content}")
    print(message_content)
except Exception as e:
    print(f"Failed to create and poll run: {e}")
