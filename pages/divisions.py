import os
import streamlit as st
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import plotly.figure_factory as ff
import plotly.graph_objs as go

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
    # Define the directory and filename
    directory = './data/parliament'
    filename = f"{directory}/members.json"
    
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Load existing members from the file, if any
    existing_members = {}
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing_members = json.load(f)
    
    # Make the API call
    url = f"https://theyvoteforyou.org.au/api/v1/people.json?key={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        fetched_members = response.json()
        
        # Check if any of the fetched members are new
        existing_ids = set(member.get('id', 'unknown_id') for member in existing_members)
        fetched_ids = set(member.get('id', 'unknown_id') for member in fetched_members)
        
        if fetched_ids - existing_ids:  # Non-empty set means new members
            # Update the member data file
            with open(filename, 'w') as f:
                json.dump(fetched_members, f)
        
        return fetched_members
    else:
        st.write(f"Failed to get data: {response.status_code}")
        return None

def count_politicians_by_party_chamber(members):
    # First, normalize the 'latest_member' field if it's nested
    members_df = pd.json_normalize(members, sep='_')
    
    # Group by 'house' and 'party', then count the members
    grouped_df = members_df.groupby(['latest_member_house', 'latest_member_party']).size().reset_index(name='Count')
    
    # Create a pivot table for easier access later
    pivot_df = pd.pivot_table(grouped_df, values='Count', index='latest_member_party', columns='latest_member_house', fill_value=0)
    
    return pivot_df

    
    return pivot_df

def find_division_by_name(divisions, target_name):
    # Use next to find the first match; defaults to None if not found
    matching_division = next((division for division in divisions if division['name'] == target_name), None)
    return matching_division

def format_division_data(division_data, members):
    individual_politicians = {}
    house = division_data['house']

    # Create a dictionary of all members by a unique identifier
    for member in members:
        latest_member = member['latest_member']
        if latest_member['house'] != house:
            continue  # Skip if the member is not from the same house as the division

        unique_id = f"{latest_member['name']['first']}_{latest_member['name']['last']}_{latest_member['party']}"
        individual_politicians[unique_id] = {
            'First Name': latest_member['name']['first'],
            'Last Name': latest_member['name']['last'],
            'Electorate': latest_member['electorate'],
            'Party': latest_member['party'],
            'Vote': 'Absent'  # Initialize everyone as 'Absent'
        }

    for vote_entry in division_data['votes']:
        vote = vote_entry['vote']
        member = vote_entry['member']
        party = member['party']
        unique_id = f"{member['first_name']}_{member['last_name']}_{party}"

        if vote == 'aye':
            individual_politicians.get(unique_id, {})['Vote'] = 'Yes'  # Update vote if exists
        else:
            individual_politicians.get(unique_id, {})['Vote'] = 'No'  # Update vote if exists

    individual_politicians_df = pd.DataFrame(list(individual_politicians.values()))

    # Compute party_vote_counts from individual_politicians_df
    party_vote_df = individual_politicians_df.groupby(['Party', 'Vote']).size().unstack(fill_value=0)
    party_vote_df['Absent'] = party_vote_df.apply(lambda row: row.sum(), axis=1) - party_vote_df['Yes'] - party_vote_df['No']

    # Define the mapping dictionary for the 'Effective Party' column
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

    # Add the 'Effective Party' column to the DataFrame
    individual_politicians_df['Effective Party'] = individual_politicians_df['Party'].map(effective_party_map)

    # Make a specialized update for Independent senators
    condition = individual_politicians_df['Effective Party'] == 'Independent'

    # Concatenate the 'First Name' and 'Last Name' columns to form the complete name
    individual_politicians_df.loc[condition, 'Effective Party'] = individual_politicians_df.loc[condition, 'First Name'] + ' ' + individual_politicians_df.loc[condition, 'Last Name']

    # Handle any NaN values that might appear if a 'Party' is not in the mapping
    individual_politicians_df['Effective Party'].fillna('Unknown', inplace=True)

    return party_vote_df, individual_politicians_df

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

def load_members_from_files():
    # Define the directory and filename
    directory = './data/parliament'
    filename = f"{directory}/members.json"
    
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
                    showlegend=(effective_party not in unique_parties)  # Show in legend only if it's the first occurrence
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
        title='vote breakdown by party',
        xaxis_title='vote',
        yaxis_title='# votes',
        barmode='stack',
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
                x=1,
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
    st.header("🗳️ parliamentary divisions 🗳️")
    st.write("control panel for investigating parliamentary divisions")

    # Set initial state
    keys = ['latest_divisions', 'members']
    default_values = [
        None, None
    ]

    for key, default_value in zip(keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default_value



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
    st.session_state['members'] = load_members_from_files()




    if st.session_state['divisions'] is not None:
        division_names = [division['name'] for key, division in st.session_state['divisions'].items()]

        members = st.session_state['members']

        selected_division_name = st.selectbox(label="select a division", options=division_names)
        selected_division_details = next(
            (division for division in st.session_state['divisions'].values() if division['name'] == selected_division_name), None)

        party_votes, individual_votes = format_division_data(selected_division_details, members)
        st.markdown(selected_division_details['summary'])


        #plot_parliament(individual_votes, selected_division_details)





        


        # # Group by 'Effective Party' and 'Vote' and then count the number of occurrences
        # effective_party_vote_df = individual_votes.groupby(['Effective Party', 'Vote']).size().unstack(fill_value=0)

        # # Calculate total votes per effective party
        # effective_party_vote_df['Total_Votes'] = effective_party_vote_df.sum(axis=1)

        # # Sort by total votes
        # sorted_effective_party_votes = effective_party_vote_df.sort_values('Total_Votes')

        # # Set default as the largest party turnout and five smallest parties
        # default_parties = [sorted_effective_party_votes.index[-1], sorted_effective_party_votes.index[:5].tolist()]

        # # Flatten the list
        # default_parties = [default_parties[0]] + default_parties[1]


        # Create a 2-column layout
        # col1, col2 = st.columns([1, 3])

        major_parties, minor_independents, all_members = st.tabs(['major parties', 'minor parties & independents', 'all members'])

        with major_parties:
            visible_parties = ['Australian Labor Party', 'Liberal National Party', 'Australian Greens']
            fig = plotly_vote_breakdown(individual_votes, visible_parties)
            st.plotly_chart(fig, use_container_width=True)
        with minor_independents:
            if selected_division_details['house'] == 'senate':
                visible_parties = [
                    'Lidia Thorpe', 'Jacqui Lambie Network', 'United Australia Party',
                    'David Pocock', 'Pauline Hanson\'s One Nation Party'
                ]
            fig = plotly_vote_breakdown(individual_votes, visible_parties)
            st.plotly_chart(fig, use_container_width=True)
        with all_members:
            if selected_division_details['house'] == 'senate':
                visible_parties = [
                    'Lidia Thorpe', 'Jacqui Lambie Network', 'United Australia Party',
                    'David Pocock', 'Pauline Hanson\'s One Nation Party',
                    'Australian Labor Party', 'Liberal National Party', 'Australian Greens'
                ]
            fig = plotly_vote_breakdown(individual_votes, visible_parties)
            st.plotly_chart(fig, use_container_width=True)
        

        # # Initialize or update the session state for checkboxes
        # if 'checkbox_state' not in st.session_state or st.session_state.checkbox_state is None:
        #     st.session_state.checkbox_state = {}
            
    #     # Initialize new entries in the checkbox_state
    #     for party in unique_parties:
    #         if party not in st.session_state.checkbox_state:
    #             st.session_state.checkbox_state[party] = party in default_parties

    #     # Now you can loop through and create checkboxes
    #     for party in unique_parties:
    #         st.session_state.checkbox_state[party] = col1.checkbox(
    #             label=f"{party}", 
    #             value=st.session_state.checkbox_state[party]
    # )

        # Now you can use st.session_state.checkbox_state to get the state of each checkbox
        # For example, to get the currently visible parties:
        
        #visible_parties = [party for party, is_checked in st.session_state.checkbox_state.items() if is_checked]



        st.dataframe(individual_votes, use_container_width=True, hide_index=True)











if __name__ == '__main__':
  main()




# Pseudocode for Parliamentary divisions

## API call to get 100 most recent divisions. Likely only needs to be run every day or so.


## Assign a UUID for each. If new UUID, add to databases. If not, do nothing. 