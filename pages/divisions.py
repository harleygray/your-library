import os
import streamlit as st
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import plotly.figure_factory as ff
import plotly.graph_objs as go
from pathlib import Path
import base64

#import matplotlib.pyplot as plt
import numpy as np

def fetch_and_store_divisions(api_key):
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

    return existing_divisions

def fetch_members(api_key):
    directory = './data/parliament'
    senate_filename = f"{directory}/senate.json"
    house_filename = f"{directory}/house.json"

    if not os.path.exists(directory):
        os.makedirs(directory)

    existing_senate_members = {}
    existing_house_members = {}

    # Load existing senate and house members
    if os.path.exists(senate_filename):
        with open(senate_filename, 'r') as f:
            existing_senate_members = json.load(f)
            
    if os.path.exists(house_filename):
        with open(house_filename, 'r') as f:
            existing_house_members = json.load(f)
    
    url = f"https://theyvoteforyou.org.au/api/v1/people.json?key={api_key}"
    response = requests.get(url)

    def flatten_member_info(member):
        latest_member = member['latest_member']
        additional_info = member.get('additional_info', {})
        
        return {
            'id': member['id'],
            'name': f"{latest_member['name']['first']} {latest_member['name']['last']}",
            'electorate': latest_member['electorate'],
            'house': latest_member['house'],
            'party': latest_member['party'],
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

def generate_unique_id(member):
    first_name = member.get('first_name') or member.get('name').split()[0]
    last_name = member.get('last_name') or member.get('name').split()[1]
    party = member.get('party', 'Unknown')
    return f"{first_name}_{last_name}_{party}"

def create_individual_politicians_dict(members):
    individual_politicians = {}
    for member in members:
        if 'name' not in member or 'party' not in member:
            st.write(f"Member entry missing 'name' or 'party': {member}")
            continue
            
        unique_id = generate_unique_id(member)
        individual_politicians[unique_id] = {
            'First Name': member['name'].split()[0],
            'Last Name': member['name'].split()[1],
            'Electorate': member.get('electorate', 'N/A'),
            'Party': member['party'],
            'Vote': 'Absent'
        }
    return individual_politicians

def update_votes(individual_politicians, votes):
    for vote_entry in votes:
        if 'member' not in vote_entry or ('name' not in vote_entry['member'] and ('first_name' not in vote_entry['member'] or 'last_name' not in vote_entry['member'])):
            st.write(f"Skipping invalid vote_entry: {vote_entry}")
            continue

        unique_id = generate_unique_id(vote_entry['member'])
        individual_politicians.get(unique_id, {}).update({
            'Vote': 'Yes' if vote_entry['vote'] == 'aye' else 'No'
        })

def format_division_data(division_data):
    if not division_data:
        st.write("Empty division_data")
        return pd.DataFrame()

    house = division_data.get('house', 'N/A')

    members = load_members_from_files(house=house)
    if not members:
        st.write("No members data to process")
        return pd.DataFrame()
    individual_politicians = create_individual_politicians_dict(members)

    update_votes(individual_politicians, division_data.get('votes', []))

    individual_politicians_df = pd.DataFrame(list(individual_politicians.values()))

    # Define the mapping dictionary for 'Effective Party' column.
    effective_party_map = {
        'Australian Greens': 'Australian Greens',
        'Australian Labor Party': 'Australian Labor Party',
        'Country Liberal Party': 'Liberal National Party',
        'DPRES': 'Australian Labor Party',
        'Independent': 'Independent',
        'Jacqui Lambie Network': 'Jacqui Lambie Network',
        'Liberal National Party': 'Liberal National Party',
        'Liberal Party': 'Liberal National Party',
        'National Party': 'Liberal National Party',
        'PRES': 'Australian Labor Party',
        'Pauline Hanson\'s One Nation Party': 'Pauline Hanson\'s One Nation Party',
        'United Australia Party': 'United Australia Party',
        'Centre Alliance': 'Independent',
        'CWM': 'Liberal National Party',
        'Katter\'s Australian Party': 'Independent',
        'SPK': 'Australian Labor Party'
    }

    # references
    # https://theyvoteforyou.org.au/people/senate/wa/sue_lines/friends
    # https://theyvoteforyou.org.au/people/senate/nt/jacinta_nampijinpa_price/friends
    # https://theyvoteforyou.org.au/people/representatives/parkes/mark_coulton/friends

    # Update 'Effective Party' based on 'Party'.
    individual_politicians_df['Effective Party'] = individual_politicians_df['Party'].map(effective_party_map)

    # Special update for Independent senators.
    condition = individual_politicians_df['Effective Party'] == 'Independent'
    individual_politicians_df.loc[condition, 'Effective Party'] = individual_politicians_df.loc[condition, 'First Name'] + ' ' + individual_politicians_df.loc[condition, 'Last Name']

    # Handle any NaN values.
    individual_politicians_df['Effective Party'].fillna('Unknown', inplace=True)


    return individual_politicians_df

# def plot_parliament(individual_votes, active_division):
#     house = active_division["house"]
    
#     if house == "senate":
#         rows = [10, 13, 15, 18, 20]
#     elif house == "representatives":
#         rows = [14, 16, 19, 21, 24, 26, 31]
    
#     fig, ax = plt.subplots()
    
#     radius = 0.7
    
#     dot_counter = 0
#     for row in rows:
#         # Calculate angle_step based on the number of dots in the current row
#         angle_step = np.pi / (row - 1) if row > 1 else 0  # Avoid division by zero
#         start_angle = np.pi  # Start from the leftmost point in the semicircle

#         for i in range(row):
#             if dot_counter >= len(individual_votes):
#                 break
            
#             vote = individual_votes.iloc[dot_counter]["Vote"]
#             dot_color = "blue" if vote == "Yes" else ("red" if vote == "No" else "gray")
            
#             angle = start_angle - i * angle_step
#             x = radius * np.cos(angle)
#             y = radius * np.sin(angle)
            
#             if house == "representatives":
#                 dot_size = 100
#             else:
#                 dot_size = 150
#             ax.scatter(x, y, c=dot_color, s=dot_size)  # Dot size increased by 2x
            
#             dot_counter += 1
        
#         radius += 0.2  # Increment the radius for the next row
    
#     ax.set_aspect("equal", "box")
#     plt.axis("off")
    
#     st.pyplot(fig)  # Display the plot using Streamlit

def load_members_from_files(house):
    # Define the directory and filename
    directory = './data/parliament'
    if (house=='senate'):
        filename = f"{directory}/senate.json"
    else:
        filename = f"{directory}/house.json"

    
    # Check if the file with all members exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        st.write("No local member data found.")
        return None

def load_divisions_from_files():
    # Define the directory and filename
    directory = './data/parliament'
    filename = f"{directory}/divisions.json"
    
    # Check if the file with all divisions exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        st.write("No local division data found.")
        return None

def plotly_vote_breakdown(individual_votes, visible_parties):
    party_color_map = {
        'Australian Greens': '#009C3D',
        'Australian Labor Party': '#E13940',
        'David Pocock': '#4ef8a6',
        'Lidia Thorpe': '#7A3535',
        'Jacqui Lambie Network': '#FFFFFF',
        'Liberal National Party': '#1C4F9C',
        'Pauline Hanson\'s One Nation Party': '#F36D24',
        'United Australia Party': '#ffed00'
    }

    # Get unique parties from the DataFrame
    unique_parties = individual_votes['Effective Party'].unique()

    # Group by 'Effective Party' and 'Vote' and then count the number of occurrences
    effective_party_vote_df = individual_votes.groupby(['Effective Party', 'Vote']).size().unstack(fill_value=0)

    # Calculate total votes per effective party
    effective_party_vote_df['Total_Votes'] = effective_party_vote_df.sum(axis=1)

    # Initialize an empty dictionary to store aggregated voting data
    aggregated_votes = {}

    # Aggregate the data from individual_votes
    for _, row in individual_votes.iterrows():
        party = row['Effective Party']
        vote = row['Vote']
        
        if party not in aggregated_votes:
            aggregated_votes[party] = {'Yes': 0, 'No': 0, 'Absent': 0}
            
        if vote == 'Yes':
            aggregated_votes[party]['Yes'] += 1
        elif vote == 'No':
            aggregated_votes[party]['No'] += 1
        else:  # Absent
            aggregated_votes[party]['Absent'] += 1

    # Instantiate bars
    vote_types = ['Yes', 'No', 'Absent']
    bars = []
    unique_parties = set()  # To keep track of unique parties for legend
    max_vote = 0  # To keep track of the maximum vote

    for vote_type in vote_types:
        for effective_party in effective_party_vote_df.index:
            # Sum all votes of this type across all parties
            sum_votes = effective_party_vote_df[vote_type].sum()
            
            # Update max_vote
            max_vote = max(max_vote, sum_votes)

            count = effective_party_vote_df.loc[effective_party, vote_type]
            if count == 0:
                continue  # Skip if count is zero
            # Set color based on whether the effective_party is in visible_parties
            color = party_color_map.get(effective_party, 'gray') if effective_party in visible_parties else 'gray'

            # Consistently set the name attribute based on the effective party
            legend_name = f"{effective_party}"

            bars.append(
                go.Bar(
                    name=legend_name,
                    x=[vote_type],
                    y=[count],
                    marker=dict(color=color),
                    hoverinfo='y+name',
                    hoverlabel=dict(namelength=-1),
                )
            )

            unique_parties.add(effective_party)  # Mark party as added to legend

    # Create figure
    fig = go.Figure(data=bars)

    # Add the dashed line
    fig.add_shape(
        go.layout.Shape(
            type='line',
            x0=min(vote_types),
            x1=max(vote_types),
            y0=39,
            y1=39,
            line=dict(
                dash='dash',
                width=4,
                color='#FFFFFF'
            ),
        )
    )

    # Change the y-axis upper limit
    y_axis_max = max(55, max_vote + 20)

    # Add Annotations and Layout
    fig.update_layout(
        #title='vote breakdown by party',
        yaxis_title='# votes',
        barmode='stack',
        margin=dict(l=0, t=0, b=0),
        legend=dict(
            x=0.5,
            y=-0.2,
            xanchor='center',
            yanchor='top',
            orientation='h'
            ),
        yaxis=dict(range=[0, y_axis_max]),
        shapes=[
            dict(
                type='line',
                yref='y',
                y0=39,
                y1=39,
                xref='paper',
                x0=0,
                x1=1,
                line=dict(dash='dash')
            ),
        ],
        annotations=[
            dict(
                x=0.1,
                y=42,
                xref='paper',
                yref='y',
                text='required Yes votes to pass',
                showarrow=False
            ),
        ],
        hovermode='x',
    )

    # Return fig object
    return fig

def main():
    # Load environment variables
    load_dotenv()

    #OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TVFY_API_KEY = os.getenv("TVFY_API_KEY")

    # Streamlit UI setup
    st.set_page_config(
        page_icon='🗳️', 
        page_title="parliamentary divisions", 
        initial_sidebar_state="collapsed",
        layout="wide")
    #st.header("🗳️ parliamentary divisions 🗳️")
    
    st.markdown("### a window into parliament")
    st.markdown('''this tool aims to display the proceedings of government in a clear way
    ''')
    #st.image('static/img/Parliament-House-Australia-Thennicke.jpg', width=400)

    #header_html = "<img src='data:static/img;base64,{}' class='img-fluid'>".format(
   #     img_to_bytes("Parliament-House-Australia-Thennicke.jpg")
    #)
    #st.markdown(
    #    header_html, unsafe_allow_html=True,
   # )

    # -----------------  loading assets  ----------------- #
    with open("static/img/Parliament-House-Australia-Thennicke.jpg", "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()
    photo_html = f'<img src="data:image/png;base64,{image_data}" width="450" alt="Parliament House" title="Parliament House"></a>'
    st.markdown(photo_html, unsafe_allow_html=True)
    
    st.divider()
    # Set initial state
    keys = ['latest_divisions', 'members']
    default_values = [
        None, None
    ]

    for key, default_value in zip(keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default_value


    with st.sidebar:
        # Update information buttons
        button1, button2 = st.columns(2)
        with button1:
            # Update member list
            if st.button('update members list'):
                with st.spinner("fetching..."):    
                    members = fetch_members(TVFY_API_KEY)
                    if members:
                        st.success("updated successfully")

        with button2:
            # Update divisions list
            if st.button('update divisions list'):
                with st.spinner("fetching..."):
                    data = fetch_and_store_divisions(TVFY_API_KEY)
                    if data:
                        st.success("updated successfully")
    





    st.session_state['divisions'] = load_divisions_from_files()




    if st.session_state['divisions'] is not None:
        division_names = [division['name'] for key, division in st.session_state['divisions'].items()]

        st.write("here you can select a 'division': a vote in either the house of representatives or the senate")
        selected_division_name = st.selectbox(label="select division", options=division_names)
        selected_division_details = next(
            (division for division in st.session_state['divisions'].values() if division['name'] == selected_division_name), None)

        individual_votes = format_division_data(selected_division_details)
        st.markdown(selected_division_details['summary'])

        #plot_parliament(individual_votes, selected_division_details)
        st.divider()
        st.write("this is a breakdown of the vote. the votes for major parties are highlighted by default, change this by clicking the other tabs")

        
        major_parties, minor_independents, all_members = st.tabs(['major parties', 'minor parties & independents', 'all members'])

        with major_parties:
            visible_parties1 = ['Australian Labor Party', 'Liberal National Party', 'Australian Greens']
            fig1 = plotly_vote_breakdown(individual_votes, visible_parties1)
            st.plotly_chart(fig1, use_container_width=True)
        with minor_independents:
            if selected_division_details['house'] == 'senate':
                visible_parties2 = [
                    'Lidia Thorpe', 'Jacqui Lambie Network', 'United Australia Party',
                    'David Pocock', 'Pauline Hanson\'s One Nation Party'
                ]
            else: 
                visible_parties2 = [
                    'Rebekha Sharkie', 'Kate Chaney''Zoe Daniel',
                    'Andrew Gee', 'Helen Haines', 'Dai Le',
                    'Monique Ryan', 'Sophie Scamps', 'Allegra Spender',
                    'Zali Steggall', 'Andrew Wilkie', 'Bob Katter'
                ]
            fig2 = plotly_vote_breakdown(individual_votes, visible_parties2)
            st.plotly_chart(fig2, use_container_width=True)
        with all_members:
            if selected_division_details['house'] == 'senate':
                visible_parties3 = [
                    'Lidia Thorpe', 'Jacqui Lambie Network', 'United Australia Party',
                    'David Pocock', 'Pauline Hanson\'s One Nation Party',
                    'Australian Labor Party', 'Liberal National Party', 'Australian Greens'
                ]
            else:
                visible_parties3 = [
                    'Rebekha Sharkie', 'Kate Chaney''Zoe Daniel',
                    'Andrew Gee', 'Helen Haines', 'Dai Le',
                    'Monique Ryan', 'Sophie Scamps', 'Allegra Spender',
                    'Zali Steggall', 'Andrew Wilkie', 'Bob Katter',
                    'Australian Labor Party', 'Liberal National Party', 'Australian Greens'
                ]
            fig3 = plotly_vote_breakdown(individual_votes, visible_parties3)
            st.plotly_chart(fig3, use_container_width=True)
        
        st.divider()
        st.write("each member's vote is also shown below")


        st.dataframe(individual_votes, use_container_width=True, hide_index=True)











if __name__ == '__main__':
  main()




# Pseudocode for Parliamentary divisions

## API call to get 100 most recent divisions. Likely only needs to be run every day or so.


## Assign a UUID for each. If new UUID, add to databases. If not, do nothing. 