import json
import requests
import os
from dotenv import load_dotenv

def fetch_members(api_key):
    # OS setup
    directory = './data/parliament'
    senate_filename = f"{directory}/senate.json"
    house_filename = f"{directory}/house.json"

    if not os.path.exists(directory):
        os.makedirs(directory)

    existing_senate_members = {}
    existing_house_members = {}
    
    url = f"https://theyvoteforyou.org.au/api/v1/people.json?key={api_key}"
    response = requests.get(url)

    # Mapping dictionary for 'Effective Party' column.
    effective_party_map = {
        'Country Liberal Party': 'Liberal National Party',
        'DPRES': 'Australian Labor Party',
        'Liberal Party': 'Liberal National Party',
        'National Party': 'Liberal National Party',
        'PRES': 'Australian Labor Party',
        'Centre Alliance': 'Independent',
        'CWM': 'Liberal National Party',
        'Katter\'s Australian Party': 'Independent',
        'SPK': 'Australian Labor Party'
    }
    # references
    # https://theyvoteforyou.org.au/people/senate/wa/sue_lines/friends
    # https://theyvoteforyou.org.au/people/senate/nt/jacinta_nampijinpa_price/friends
    # https://theyvoteforyou.org.au/people/representatives/parkes/mark_coulton/friends



    def flatten_member_info(member):
        latest_member = member['latest_member']
        party = latest_member['party']
        effective_party = effective_party_map.get(party, party)  # Get effective party from map, or use original party if not found

        additional_info = member.get('additional_info', {})

        return {
            'id': member['id'],
            'name': f"{latest_member['name']['first']} {latest_member['name']['last']}",
            'electorate': latest_member['electorate'],
            'house': latest_member['house'],
            'party': latest_member['party'],
            'effective_party': effective_party,
            'rebellions': additional_info.get('rebellions'),
            'votes_attended': additional_info.get('votes_attended'),
            'votes_possible': additional_info.get('votes_possible'),
            'offices': [office['position'] for office in additional_info.get('offices', [])]
        }
    
    if response.status_code == 200:
        fetched_members = response.json()
        
        senate_members = []
        house_members = []

        for member in fetched_members:
            member_id = member.get('id', 'unknown_id')
            
            # Fetch additional info
            additional_info = fetch_additional_info(member_id, api_key)
            # If additional info is fetched, update the member dictionary
            if additional_info:
                member['additional_info'] = additional_info
            
            # Flatten and filter member information
            flat_member = flatten_member_info(member)

            house = flat_member['house']
            if house == 'senate':
                senate_members.append(flat_member)
            elif house == 'representatives':
                house_members.append(flat_member)
        
        # Save to files
        if senate_members:
            with open(senate_filename, 'w') as f:
                json.dump(senate_members, f)
        
        if house_members:
            with open(house_filename, 'w') as f:
                json.dump(house_members, f)
                
        return senate_members, house_members

    else:
        # Handle the failure case
        return None, None
    
def fetch_additional_info(member_id, api_key):
    url = f"https://theyvoteforyou.org.au/api/v1/people/{member_id}.json?key={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None



if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("TVFY_API_KEY")

    fetch_members(api_key)
