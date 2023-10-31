import os
import streamlit as st
import requests
import json
import pandas as pd
from dotenv import load_dotenv
import plotly.graph_objs as go
import base64
import re

def create_individual_politicians_dict(members):
    individual_politicians = {}
    for member in members:
        unique_id = generate_unique_id(member)  # Assuming this function is compatible
        first_name, last_name = member['name'].split()[:2]
        individual_politicians[unique_id] = {
            'First Name': first_name,
            'Last Name': last_name,
            'Electorate': member.get('electorate', 'N/A'),
            'Party': member['party'],
            'Effective Party': member.get('effective_party', member['party']),  # Use 'party' as a fallback
            'Color': member.get('color', 'gray'),  # Default to gray if color is not provided
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

@st.cache_data()
def format_division_data(division_data):
    if not division_data:
        st.write("Empty division_data")
        return pd.DataFrame()

    house = division_data.get('house', 'N/A')

    members = st.session_state.get(house, [])  # Safely get the members data

    if not members:
        st.write("No members data to process")
        return pd.DataFrame()

    individual_politicians = create_individual_politicians_dict(members)

    update_votes(individual_politicians, division_data.get('votes', []))

    individual_politicians_df = pd.DataFrame(list(individual_politicians.values()))

    

    # Special update for Independent senators.
    condition = individual_politicians_df['Effective Party'] == 'Independent'
    individual_politicians_df.loc[condition, 'Effective Party'] = individual_politicians_df.loc[condition, 'First Name'] + ' ' + individual_politicians_df.loc[condition, 'Last Name']

    # Handle any NaN values.
    individual_politicians_df['Effective Party'].fillna('Unknown', inplace=True)

    return individual_politicians_df

def plot_parliament(individual_votes, active_division):
    


    fig = go.Figure(data=go.Scatter(
        x=[1, 2, 3, 4],
        y=[10, 11, 12, 13],
        mode='markers',
        marker=dict(size=[40, 60, 80, 100],
                    color=[0, 1, 2, 3])
    ))
    return fig

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

@st.cache_data()
def load_vote_template(filename):
    # Check if the file with all members exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        st.write("No local member data found.")
        return None

@st.cache_data()
def load_members_from_files(filename):
    # Check if the file with all members exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        st.write("No local member data found.")
        return None

@st.cache_data()
def load_divisions_from_files():
    # Define the directory and filename
    directory = './data/parliament'
    filename = f"{directory}/divisions.json"
    
    # Check if the file with all divisions exists
    if os.path.exists(filename):
        # Load data from the file if it exists
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        st.write("No local division data found.")
        return None

@st.cache_data()
def plotly_vote_breakdown(individual_votes, visible_parties):
    # For coloring data visualisations
    party_color_map = {
        'Australian Greens': '#009C3D',
        'Australian Labor Party': '#E13940',
        'David Pocock': '#4ef8a6',
        'Lidia Thorpe': '#7A3535',
        'Jacqui Lambie Network': '#FFFFFF',
        'Liberal National Party': '#1C4F9C',
        'Pauline Hanson\'s One Nation Party': '#F36D24',
        'United Australia Party': '#ffed00' # todo - add more
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


            # Show legend based on whether the effective party has been added yet
            if effective_party not in unique_parties:
                showlegend = True
                unique_parties.add(effective_party)  # Mark the effective party as added
            else:
                showlegend = False


            # Set color based on whether the effective_party is in visible_parties
            color = party_color_map.get(effective_party, 'gray') if effective_party in visible_parties else 'gray'

            legend_name = f"{effective_party}"

            bars.append(
                go.Bar(
                    name=legend_name,
                    showlegend=showlegend,
                    x=[vote_type],
                    y=[count],
                    marker=dict(color=color),
                    hoverinfo='y+name',
                    hoverlabel=dict(namelength=-1),
                    legendgroup=effective_party
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
        clickmode='none',
        dragmode=False,
        margin=dict(l=0, t=0, b=0),
        legend=dict(
            x=0.5,
            y=-0.2,
            xanchor='center',
            yanchor='top',
            orientation='h'
            ),
        yaxis=dict(
            range=[0, y_axis_max],
            fixedrange=True
            ),
        xaxis=dict(fixedrange=True),
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

def generate_unique_id(member):
    first_name = member.get('first_name') or member.get('name').split()[0]
    last_name = member.get('last_name') or member.get('name').split()[1]
    party = member.get('party', 'Unknown')
    return f"{first_name}_{last_name}_{party}"

def categorise_divisions(division_names):
    categories = {
        'Matters of Urgency': [],
        'Business': [],
        'Documents': [],
        'Committees': [],
        'Motions': [],
        'Bills': {}
    }

    for division in division_names:
        categorized = False
        for category in categories.keys():
            if division.startswith(category):
                clean_name = division[len(category) + 3:]  # +3 to remove the " - " as well
                categories[category].append(clean_name)
                categorized = True
                break
        if not categorized:
            bill_split = re.split(r'(\d{4}(?:-\d{4})?) - ', division)
            if len(bill_split) >= 3:
                bill_title = bill_split[0] + bill_split[1]
                bill_stage = bill_split[2]
                categories['Bills'].setdefault(bill_title, []).append(bill_stage)
    return categories

@st.cache_data()
def return_division(full_name, divisions):
    division = next(
        (division for division in divisions.values() if division['name'] == full_name), None)
    return division

@st.cache_data()
def background_image(content1, content2):
    with open("static/img/Parliament-House-Australia-Thennicke.jpg", "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()
    
    background_image_html = f'url(data:image/png;base64,{image_data})'
    st.markdown(
        f'<h1 style="text-align:center;background-image: {background_image_html};background-size: 100% 100%;'
        f'font-size:60px;border-radius:2%;padding-top:35%;padding-bottom:10%;">'  
        f'<span style="background-color: rgb(69,69,92,0.5); color:white;font-size:40px;">{content1}</span><br>'
        f'<span style="background-color: rgb(69,69,92,0.6); color:white;font-size:19px;">{content2}</span></h1>',
        unsafe_allow_html=True
    )





    # st.markdown(f'<h1 style="text-align:center;background-image: linear-gradient(to right,{color1}, {color2});font-size:60px;border-radius:2%;">'
    #             f'<span style="color:{color3};">{content1}</span><br>'
    #             f'<span style="color:white;font-size:17px;">{content2}</span></h1>', 
    #             unsafe_allow_html=True)


def main():
    # Load environment variables
    load_dotenv()
    TVFY_API_KEY = os.getenv("TVFY_API_KEY")

    # Streamlit UI setup
    st.set_page_config(
        page_icon='🗳️', 
        page_title="parliamentary divisions", 
        initial_sidebar_state="collapsed",
        layout="centered")
    
    # Set initial state
    keys = ['divisions', 'senate', 'representatives', 'selected_division']
    default_values = [None, None, None, None]

    for key, default_value in zip(keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default_value

    
    
    st.session_state['representatives'] = load_members_from_files('./data/parliament/house.json')
    st.session_state['senate'] = load_members_from_files('./data/parliament/senate.json')
    st.session_state['divisions'] = load_divisions_from_files()

    # Header
    background_image("window into parliament", "a tool to clearly display the proceedings of government")
    st.write()

    #st.markdown(photo_html, unsafe_allow_html=True)
    
    
    if st.session_state['divisions'] is None or st.session_state['senate'] is None or st.session_state['representatives'] is None:
        st.write('data not loaded in yet')
    else:
        st.write("⬇️ select a type of 'division': a vote in either the house of representatives or the senate")
        
        col1, col2 = st.columns([0.3,0.7])
        division_names = [division['name'] for key, division in st.session_state['divisions'].items()]
        
        divisions_dict = categorise_divisions(division_names)
        with col1:
            selected_division_category =  st.radio(label='pick a type of division', options=list(divisions_dict.keys()))
        
        with col2:
            if selected_division_category == 'Bills':
                selected_bill_name = st.selectbox(label='pick a bill', options=list(divisions_dict['Bills'].keys()))
                if len(divisions_dict['Bills'][selected_bill_name]) == 1:
                    full_name = selected_bill_name + ' - ' + divisions_dict['Bills'][selected_bill_name][0]
                else:
                    selected_bill_reading = st.selectbox(label='which division?', options=list(divisions_dict['Bills'][selected_bill_name]))
                    full_name = selected_bill_name + ' - ' + selected_bill_reading
                
            else:
                selected_division = st.selectbox(label='pick a division', options=list(divisions_dict[selected_division_category]))
                full_name = selected_division_category + ' - ' + selected_division
        
        # Hold selected division in session state
        st.session_state['selected_division'] = return_division(full_name, st.session_state['divisions'])
        
        individual_votes = format_division_data(st.session_state['selected_division'])

        # Dictionary to classify parties as major vs minor/independent
        party_dict = {
            'major_parties': {
                'senate': ['Australian Labor Party', 'Liberal National Party', 'Australian Greens'],
                'representatives': ['Australian Labor Party', 'Liberal National Party', 'Australian Greens']
            },
            'minor_independents': {
                'senate': ['Lidia Thorpe', 'Jacqui Lambie Network', 'United Australia Party', 'David Pocock', 'Pauline Hanson\'s One Nation Party'],
                'representatives': ['Rebekha Sharkie', 'Kate Chaney', 'Zoe Daniel', 'Andrew Gee', 'Helen Haines', 'Dai Le', 'Monique Ryan', 'Sophie Scamps', 'Allegra Spender', 'Zali Steggall', 'Andrew Wilkie', 'Bob Katter']
            },
            'all_members': {
                'senate': [],  # will populate this below
                'representatives': []  # will populate this below
            }
        }
        party_dict['all_members']['senate'] = party_dict['major_parties']['senate'] + party_dict['minor_independents']['senate']
        party_dict['all_members']['representatives'] = party_dict['major_parties']['representatives'] + party_dict['minor_independents']['representatives']

        selected_house = st.session_state['selected_division']['house']

        # Generate figures 
        fig_major = plotly_vote_breakdown(individual_votes, party_dict['major_parties'][selected_house])
        fig_minor = plotly_vote_breakdown(individual_votes, party_dict['minor_independents'][selected_house])
        fig_all = plotly_vote_breakdown(individual_votes, party_dict['all_members'][selected_house])

        # Display figures
        major_parties, minor_independents, all_members = st.tabs(['major parties', 'minor parties & independents', 'all members'])
        with major_parties:
            #st.markdown(
            #    f'<h1 style="text-align:center;background-image: {background_image_html};background-size: 100% 100%;'
            #    f'font-size:60px;border-radius:2%;padding-top:35%;padding-bottom:10%;">'  
            #    f'<span style="background-color: rgb(69,69,92,0.6); color:white;font-size:19px;">{st.session_state['selected_division']['name']}#</span></h1>',
            #    unsafe_allow_html=True


            #)
            st.subheader(st.session_state['selected_division']['name'])
            st.plotly_chart(fig_major, use_container_width=True)
        with minor_independents:
            st.subheader(st.session_state['selected_division']['name'])
            st.plotly_chart(fig_minor, use_container_width=True)
        with all_members:
            st.subheader(st.session_state['selected_division']['name'])
            st.plotly_chart(fig_all, use_container_width=True)
        
        with st.expander("individual member votes"):
            st.dataframe(individual_votes, use_container_width=True, hide_index=True)

        st.markdown(st.session_state['selected_division']['summary'])
        st.divider()
            


if __name__ == '__main__':
  main()

