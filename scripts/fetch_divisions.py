import os
from dotenv import load_dotenv
import json
import requests

def fetch_divisions(api_key):
    # Define the directory and filename for storing divisions
    directory = './data/parliament'
    filename = f"{directory}/divisions.json"
    
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Fetch the most recent 100 divisions
    url = f"https://theyvoteforyou.org.au/api/v1/divisions.json?key={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        st.write(f"Failed to get divisions: {response.status_code}")
        return None
    
    recent_divisions = response.json()
    
    # Load existing divisions from the file, if any
    existing_divisions = {}
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing_divisions = json.load(f)
    
    # Iterate through each division to get details
    for division in recent_divisions:
        division_id = division.get('id', 'unknown_id')
        if division_id not in existing_divisions:
            # Fetch details of the new division
            detail_url = f"https://theyvoteforyou.org.au/api/v1/divisions/{division_id}.json?key={api_key}"
            detail_response = requests.get(detail_url)
            if detail_response.status_code == 200:
                division_detail = detail_response.json()
                
                # Store new division details
                existing_divisions[division_id] = division_detail
    
    # Save all division data back to the file
    with open(filename, 'w') as f:
        json.dump(existing_divisions, f)


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("TVFY_API_KEY")
    fetch_divisions(api_key)