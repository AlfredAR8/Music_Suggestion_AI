from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

# Initialize the OpenAI client with your API key
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)


# Create the assistant
assistant = client.beta.assistants.create(
    name="Music Suggestions",
    instructions="You are an expert music analyst. Use your knowledge base to answer questions about which song fits more for me. Also just answer only with the song name and song artists for each song you recommend.",
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

with open('playlist.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

json_string = json.dumps(data).replace('"', '\\"')

# Create a thread and attach the files to the message
try:
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"Search for the following songs in the database: \n{json_string} For each matched song, look for its “popularity”, “duration_ms”, “explicit”, “danceability”, “energy”, “key”, “loudness”, “mode”, “speechiness”, “acousticness”, “instrumentalness”, “liveness”, “valence”, “tempo”, “time_signature”, and “track_genre” details. Based on these songs and their attributes, identify 5 similar songs from the database that I may like and provide only the name an artist of each song.",
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