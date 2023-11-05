import edgedb
import streamlit as st
import datetime
from dotenv import load_dotenv
import os
import json
import requests
import re
from itertools import groupby
from operator import attrgetter
import pandas as pd

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
def extract_info(json_data):   
    unique_parties = set()
    unique_offices = set()
    
    for item in json_data:
        # Add the party to the set of unique parties
        unique_parties.add(item['party'])
        
        # Add each office to the set of unique offices
        for office in item.get('offices', []):
            unique_offices.add(office)
            
    return list(unique_parties), list(unique_offices)

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
        #st.write("No local division data found.")
        return None

def fetch_additional_info(member_id, api_key):
    url = f"https://theyvoteforyou.org.au/api/v1/people/{member_id}.json?key={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

@st.cache_data()
def unique_party_combinations(json_data):
    unique_combinations = set()

    for item in json_data:
        party_combo = (item['party'], item['effective_party'])
        # Add the tuple to the set only if the two items are different
        if party_combo[0] != party_combo[1]:
            unique_combinations.add(party_combo)

    return unique_combinations

@st.cache_data()
def division_category(division_name):
    categories = {
        'Matters of Urgency': [],
        'Business': [],
        'Documents': [],
        'Committees': [],
        'Motions': [],
        'Bills and Amendments': {}
    }

    categorised_division = {
        'DivisionCategory': None,
        'DivisionSubcategory': None,
        'DivisionSubsubcategory': None
    }
    

    if division_name.startswith('Committees'):
        match = re.match(r'^(.*?) - (.*?); (.*)$', division_name)
        if match:
            categorised_division = {
                'DivisionCategory': match.group(1),
                'DivisionSubcategory': match.group(2),
                'DivisionSubsubcategory': match.group(3)
            }
        else:
            match = re.match(r'^(.*?) - (.*?) - (.*)$', division_name)
            if match:
                categorised_division = {
                    'DivisionCategory': match.group(1),
                    'DivisionSubcategory': match.group(2),
                    'DivisionSubsubcategory': match.group(3)
                }
    elif (division_name.startswith('Matters of Urgency') or 
        division_name.startswith('Documents') or
        division_name.startswith('Motions') or 
        division_name.startswith('Business')):
        division_split = re.split(r' - ', division_name)
        for i in range(len(division_split)):
            if i == 0:
                categorised_division['DivisionCategory']=division_split[i]
            if i == 1:
                categorised_division['DivisionSubcategory']=division_split[i]
            if i == 2:
                categorised_division['DivisionSubsubcategory']=division_split[i]
        
    else:
        division_name_split = division_name.split(' - ',1)
        categorised_division = {
            'DivisionCategory': 'Bills and Amendments',
            'DivisionSubcategory': division_name_split[0],
            'DivisionSubsubcategory': division_name_split[1]
        }

        
    return categorised_division

def main():
    # Load environment variables
    load_dotenv()
    TVFY_API_KEY = os.getenv("TVFY_API_KEY")

    # Streamlit UI setup
    st.set_page_config(
        page_icon='🗳️', 
        page_title="EdgeDB", 
        initial_sidebar_state="expanded",
        layout="centered")

    senators_json = load_members_from_files('./data/parliament/senate.json')
    mps_json = load_members_from_files('./data/parliament/house.json')

    senate_info = extract_info(senators_json)
    mps_info = extract_info(mps_json)
    #st.write('unique parties:')
    #st.write(senate_info[0])
    #st.write('unique offices:')
    #st.write(senate_info[1])
    
    #unique_allegiances = unique_party_combinations(senators_json)
    #st.write('unique combinations of party/effective party:')
    #st.write(unique_allegiances)

    #st.json(fetch_additional_info(10904,TVFY_API_KEY))

    with st.container():
        st.markdown('#### Handy utilities')
        cheet_sheet_col, api_doc_col, easy_edgedb_col, admin_cmds = st.columns([1, 1, 1, 1])
        with cheet_sheet_col:
            st.markdown(
                '[EdgeDB Cheat Sheet](https://www.edgedb.com/docs/guides/cheatsheet/index)')
        with api_doc_col:
            st.markdown(
                '[EdgeDB-Python API docs](https://www.edgedb.com/docs/clients/python/api/blocking_client#edgedb-python-blocking-api-reference)')
        with easy_edgedb_col:
            st.markdown('[Easy EdgeDB](https://www.edgedb.com/easy-edgedb)')
        with admin_cmds:
            st.markdown('[Admin Commands](https://www.edgedb.com/docs/guides/cheatsheet/admin#ref-cheatsheet-admin)')

    client = edgedb.create_client()

    # Load senate divisions
    divisions = load_divisions_from_files()
    senate_divisions = {}
    house_divisions = {}
    for division_id, division_data in divisions.items():
        if division_data['house'] == 'senate':
            senate_divisions[division_id] = division_data
        elif division_data['house'] == 'representatives':
            house_divisions[division_id] = division_data

    debug = st.container()

    with st.sidebar:
        if st.button('add all unique offices'):
            for office in senate_info[1]:
                client.query("""
                    insert parliament::Office { 
                        name := <str>$office 
                    }
                    unless conflict on .name
                    else parliament::Office
                    """,
                    office=office
                )
            for office in mps_info[1]:
                client.query("""
                    insert parliament::Office { 
                        name := <str>$office 
                    }
                    unless conflict on .name
                    else parliament::Office
                    """,
                    office=office
                )
            st.toast('added offices', icon='✅')

        if st.button('add all parties'):
            for party_name in senate_info[0]:
                client.query("""
                    insert parliament::Party {
                        name := <str>$name
                    }
                    unless conflict on .name
                    else parliament::Party
                    """, 
                    name=party_name)
            
            st.toast('added parties from senate', icon='✅')

            for party_name in mps_info[0]:
                client.query("""
                    insert parliament::Party {
                        name := <str>$name
                    }
                    unless conflict on .name
                    else parliament::Party
                    """, 
                    name=party_name
                )
            st.toast('added parties from house', icon='✅')

        if st.button('add members and senators info'):
            for item in senators_json:
                client.query("""
                    insert parliament::Member { 
                        full_name := <str>$full_name,
                        house :=  <str>$house,
                        person_id := <int16>$person_id,
                        offices := (select parliament::Office filter .name IN array_unpack(<array<str>>$offices)),
                        electorate := <str>$electorate,
                        party := assert_single((select parliament::Party filter .name = <str>$party))
                    }
                    unless conflict on .person_id
                    else parliament::Member""", 
                full_name=item['name'],
                house=item['house'],
                person_id=item['id'],
                offices=item['offices'],
                electorate=item['electorate'],
                party=item['party']
                )
            st.toast('added senators', icon='✅')

            for item in mps_json:
                client.query("""
                    insert parliament::Member { 
                        full_name := <str>$full_name,
                        house :=  <str>$house,
                        person_id := <int16>$person_id,
                        offices := (select parliament::Office filter .name IN array_unpack(<array<str>>$offices)),
                        electorate := <str>$electorate,
                        party := assert_single(
                            (select parliament::Party filter .name = <str>$party))
                    }
                    unless conflict on .person_id
                    else parliament::Member""", 
                full_name=item['name'],
                house=item['house'],
                person_id=item['id'],
                offices=item['offices'],
                electorate=item['electorate'],
                party=item['party']
                )
            st.toast(f'added mps', icon='✅')

        if st.button('add votes'):
            for division_id, division_data in divisions.items():
                client.query("""
                    insert parliament::Division { 
                        division_id := <int16>$division_id,
                        house := <str>$house,
                        name := <str>$name,
                        date := <str>$date,
                        clock_time := <str>$clock_time,
                        aye_votes := <int16>$aye_votes,
                        no_votes := <int16>$no_votes,
                        possible_turnout := <int16>$possible_turnout,
                        summary := <str>$summary
                    }
                    unless conflict on .division_id
                    else parliament::Division""", 
                division_id=division_data['id'],
                house=division_data['house'],
                name=division_data['name'],
                date=division_data['date'],
                clock_time=division_data['clock_time'],
                aye_votes=division_data['aye_votes'],
                no_votes=division_data['no_votes'],
                possible_turnout=division_data['possible_turnout'],
                summary=division_data['summary']
                )
                

                for vote in division_data['votes']:
                    print(f"Current member_id: {vote['member']['person']['id']}") 
                    
                    client.query("""
                        insert parliament::DivisionVote { 
                            division := (select parliament::Division filter .division_id = <int16>$division_id),
                            member :=  assert_single((select parliament::Member filter .person_id = <int16>$member_id)),
                            vote := <str>$vote
                        } 
                        unless conflict on ((.member, .division)) 
                        else parliament::DivisionVote;               
                        """, 
                        division_id=division_data['id'],
                        member_id=vote['member']['person']['id'],
                        vote=vote['vote'],
                        )
                st.toast(f'added votes for {division_data["name"]}', icon='✅')


        if st.button('update divisions with categories'):
            for item in senate_divisions.values():
                division_categories= division_category(item['name'])
                debug.write(division_categories)

                client.query("""
                    with division_category := (
                        insert parliament::DivisionCategory {
                            category_name := <str>$division_category,
                        }
                        unless conflict on .category_name
                        else parliament::DivisionCategory
                    ),
                    division_subcategory := (
                        insert parliament::DivisionSubcategory {
                            category_name := <str>$division_subcategory,
                            category := division_category
                        }
                        unless conflict on .category_name
                        else parliament::DivisionSubcategory
                    ),
                    division_subsubcategory := (
                        if (select <str>$division_subsubcategory != '') then (
                            insert parliament::DivisionSubsubcategory {
                                category_name := <str>$division_subsubcategory,
                                subcategory := division_subcategory
                            }
                            unless conflict on .category_name
                            else parliament::DivisionSubsubcategory
                        ) else (select {} limit 0)
                    ),
                    select division_category {*}
                    """,
                    division_category=division_categories['DivisionCategory'],
                    division_subcategory=division_categories['DivisionSubcategory'],
                    division_subsubcategory=division_categories['DivisionSubsubcategory'] or ''
                )   


                client.query("""
                    update parliament::Division
                    filter .division_id = <int16>$division_id
                    set { 
                        division_category := (
                            select parliament::DivisionCategory 
                            filter .category_name = <str>$division_category
                        ),
                        division_subcategory := (
                            select parliament::DivisionSubcategory 
                            filter .category_name = <str>$division_subcategory
                        ),
                        division_subsubcategory := (
                            if (select <str>$division_subsubcategory != '') then (
                                select parliament::DivisionSubsubcategory 
                                filter .category_name = <str>$division_subsubcategory
                            ) else (select {} limit 0)
                        )
                    }                 
                    """, 
                    division_id=item['id'],
                    division_category=division_categories['DivisionCategory'],
                    division_subcategory=division_categories['DivisionSubcategory'],
                    division_subsubcategory=division_categories['DivisionSubsubcategory'] or ''
                )
            st.toast(f'ran update', icon='✅')

    with st.expander("select division"):
        division_categories = client.query("""
            select distinct(parliament::DivisionCategory {
                category_name
            })"""
        )
        category_names = map(lambda category: category.category_name, division_categories)
        selected_division_category =  st.radio(label='pick a type of division', options=list(category_names))

        division_subcategories = client.query("""
            select distinct(parliament::DivisionSubcategory {
                category_name
            }) filter .category = (select parliament::DivisionCategory filter .category_name = <str>$selected_division_category)""",
            selected_division_category=selected_division_category
        )
        
        st.dataframe(
            list(category.category_name for category in division_subcategories)
        )

    st.subheader('select all divisions a member voted in')
    all_members = client.query("""
        select distinct(parliament::Member {
            full_name,
            party: { name }
        })"""
    )
    
    member_names = map(lambda category: category.full_name + ", " + category.party.name, all_members)

    # First, sort all_members by party.name
    all_members_sorted = sorted(all_members, key=attrgetter('party.name'))

    # Then, use groupby to group them by party.name
    grouped_members = groupby(all_members_sorted, key=attrgetter('party.name'))

    # Now, grouped_members is an iterable of tuples, where the first element is the party name,
    # and the second element is an iterable of members in that party.
    # You can convert it to a dictionary where the party name is the key and the value is a list of member names:
    member_names_by_party = {party: list(map(attrgetter('full_name'), members)) for party, members in grouped_members}
    
    party_col, member_col = st.columns(2)

    with party_col: 
        selected_party = st.multiselect(label='which parties?', options=list(member_names_by_party.keys()))
    # Assuming 'selected_party' is a list of parties chosen with st.multiselect
    for party in selected_party:  # Iterate over all selected options
        st.write(member_names_by_party.get(party, "No members found for selected party"))

    # Check if a party has been selected and not empty
    if selected_party:  
        party_members_options = [member for party in selected_party for member in member_names_by_party.get(party, [])]
    else:
        # If no party is selected, show all members
        party_members_options = [member for members in member_names_by_party.values() for member in members]

    with member_col:
        selected_member_names = st.multiselect(label='which member?', options=party_members_options)

    # show all divisions. [division_name], division_outcome, member_vote1, ...member_vote_n,
    
    divisions = client.query("""
        with member := (
            select parliament::Member 
            filter .full_name in array_unpack(<array<str>>$selected_member_names)
        )
        select parliament::Division {**} {
            division_name := .name,
            member_votes := (
                select .votes {
                    member_name := .member.full_name,
                    vote := .vote
                }
                filter .member.full_name in array_unpack(<array<str>>$selected_member_names)     
            )
        } 
        filter .member_votes.member_name in array_unpack(<array<str>>$selected_member_names)""",
        selected_member_names=selected_member_names)

    #all_divisions_sorted = sorted(divisions, key=attrgetter('division_name'))
    #grouped_divisions_members = groupby(all_divisions_sorted, key=attrgetter('member_votes.member_name'))
    
    # Flatten the data
    flattened_data = [
        {
            "division_name": obj.division_name,
            "member_name": vote.member_name,
            "vote": vote.vote,
        }
        for obj in divisions
        for vote in obj.member_votes
    ]

    # Create a DataFrame
    df = pd.DataFrame(flattened_data)

    # Pivot the DataFrame to get one column per member
    pivot_df = df.pivot_table(index="division_name", columns="member_name", values="vote", aggfunc='first')
    
    st.dataframe(pivot_df)
    #st.write(senate_divisions.values())
    # result = client.query("""
    #     select parliament::Division {**} limit 5
    # """)

    

    #st.json(result)

    # result = client.query_single("""
    #     INSERT parliament::Party {
    #         name := <str>$name,
    #         plotly_col := <str>$plotly_col
    #     }
    # """, name="Australian Labor Party", plotly_col='#E13940')

    #st.write(result)

    

if __name__ == '__main__':
  main()