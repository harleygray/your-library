import os
import streamlit as st
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import plotly.figure_factory as ff
import plotly.graph_objs as go

import matplotlib.pyplot as plt
import numpy as np

def fetch_divisions(api_key):
    url = f"https://theyvoteforyou.org.au/api/v1/divisions.json?key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.write(f"Failed to get data: {response.status_code}")
        return None

def fetch_members(api_key):
    url = f"https://theyvoteforyou.org.au/api/v1/people.json?key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.write(f"Failed to get data: {response.status_code}")
        return None

def division_details(api_key, divisions, target_name):
    division_id = next((division for division in divisions if division['name'] == target_name), None)['id']
    url = f"https://theyvoteforyou.org.au/api/v1/divisions/{division_id}.json?key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
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

def display_division(division):
    st.markdown(f"### Division Details")
    
    st.write(f"**ID**: {division['id']}")
    st.write(f"**House**: {division['house']}")
    st.write(f"**Name**: {division['name']}")
    st.write(f"**Date**: {division['date']}")
    st.write(f"**Number**: {division['number']}")
    st.write(f"**Clock Time**: {division['clock_time']}")
    st.write(f"**Aye Votes**: {division['aye_votes']}")
    st.write(f"**No Votes**: {division['no_votes']}")
    st.write(f"**Possible Turnout**: {division['possible_turnout']}")
    st.write(f"**Rebellions**: {division['rebellions']}")
    st.write(f"**Edited**: {division['edited']}")

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
    
    return party_vote_df, individual_politicians_df

def plot_parliament(individual_votes, active_division):
    house = active_division["house"]
    
    if house == "senate":
        rows = [10, 13, 15, 18, 20]
    elif house == "representatives":
        rows = [14, 16, 19, 21, 24, 26, 31]
    
    fig, ax = plt.subplots()
    
    radius = 0.7
    
    dot_counter = 0
    for row in rows:
        # Calculate angle_step based on the number of dots in the current row
        angle_step = np.pi / (row - 1) if row > 1 else 0  # Avoid division by zero
        start_angle = np.pi  # Start from the leftmost point in the semicircle

        for i in range(row):
            if dot_counter >= len(individual_votes):
                break
            
            vote = individual_votes.iloc[dot_counter]["Vote"]
            dot_color = "blue" if vote == "Yes" else ("red" if vote == "No" else "gray")
            
            angle = start_angle - i * angle_step
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            
            if house == "representatives":
                dot_size = 100
            else:
                dot_size = 150
            ax.scatter(x, y, c=dot_color, s=dot_size)  # Dot size increased by 2x
            
            dot_counter += 1
        
        radius += 0.2  # Increment the radius for the next row
    
    ax.set_aspect("equal", "box")
    plt.axis("off")
    
    st.pyplot(fig)  # Display the plot using Streamlit


def main():
    # Load environment variables
    load_dotenv()

    #OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TVFY_API_KEY = os.getenv("TVFY_API_KEY")

    # Streamlit UI setup
    st.set_page_config(page_icon='🗳️', page_title="parliamentary divisions", initial_sidebar_state="collapsed")
    st.header("🗳️ parliamentary divisions 🗳️")
    st.write("control panel for investigating parliamentary divisions")

    # Set initial state
    keys = ['latest_divisions']
    default_values = [
        None
    ]

    for key, default_value in zip(keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default_value

    # Fetch member information
    members = fetch_members(TVFY_API_KEY)
    count_politicians_by_party = count_politicians_by_party_chamber(members)
    #st.write(count_politicians_by_party)
    #st.write(members[0:3])

    # Call Divisions API
    if st.button('fetch divisions'):
        with st.spinner("fetching..."):    
            data = fetch_divisions(TVFY_API_KEY)
            if data:
                st.write("Data fetched successfully.")
                st.session_state["latest_divisions"] = data
                st.json(st.session_state["latest_divisions"])


    

    if st.session_state["latest_divisions"] is not None:
        division_names = [division['name'] for division in st.session_state["latest_divisions"]]

        selected_division = st.selectbox(label="select a division", options=division_names)
        selected_division_details = division_details(
            api_key=TVFY_API_KEY, 
            divisions=st.session_state["latest_divisions"], 
            target_name=selected_division)


        party_votes, individual_votes = format_division_data(selected_division_details, members)
        st.markdown(selected_division_details['summary'])
        st.write(individual_votes)
        st.write(party_votes)
        st.write(selected_division_details)
        #display_division(selected_division_details)
        #display_division(st.session_state["latest_divisions"][0])

        # Assuming individual_politicians_df and party_vote_df are already created
        # Mapping parties to their colors
        party_color_map = {
            'Australian Greens': '#009C3D',
            'Australian Labor Party': '#E13940',
            'Country Liberal Party': '#ff6900',
            'DPRES': '#000080',
            'Independent': '#808080',
            'Jacqui Lambie Network': '#000000',
            'Liberal National Party': '#1C4F9C',
            'Liberal Party': '#1C4F9C',
            'National Party': '#FFF200',
            'PRES': '#000080',
            'Pauline Hanson\'s One Nation Party': '#0176BC',
            'United Australia Party': '#ffed00'
        }




        plot_parliament(individual_votes, selected_division_details)

        # Assuming you have party_vote_df DataFrame
        vote_types = ['Yes', 'No', 'Absent']
        bars = []

        for vote_type in vote_types:
            for party in party_votes.index:
                count = party_votes.loc[party, vote_type]
                if count == 0:
                    continue  # Skip if count is zero
                color = party_color_map.get(party, '#000000')  # Default to black

                bars.append(
                    go.Bar(
                        name=f"{party}",
                        x=[vote_type],
                        y=[count],
                        marker=dict(color=color),
                        hoverinfo='y+name',
                        hoverlabel=dict(namelength=-1)  # Allow the label to expand as needed
                    )
                )

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
                    width=1,
                    color='black',
                ),
            )
        )

        # Add Annotations and Layout
        fig.update_layout(
            title='Votes By Type',
            xaxis_title='Vote Type',
            yaxis_title='Votes',
            barmode='stack',
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
                    x=0,
                    y=39,
                    xref='paper',
                    yref='y',
                    text='required Yes votes to pass',
                    showarrow=False
                ),
            ],
            plot_bgcolor='#A6A6A6',
            paper_bgcolor='#A6A6A6',
            hovermode='x',
        )

        # Streamlit Plotly chart
        st.plotly_chart(fig, use_container_width=True)









if __name__ == '__main__':
  main()




# Pseudocode for Parliamentary divisions

## API call to get 100 most recent divisions. Likely only needs to be run every day or so.


## Assign a UUID for each. If new UUID, add to databases. If not, do nothing. 