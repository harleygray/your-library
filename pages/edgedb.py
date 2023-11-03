import edgedb
import streamlit as st
import datetime
from dotenv import load_dotenv
import os
import json


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


#def define_allegiance(json_data):


@st.cache_data()
def unique_party_combinations(json_data):
    unique_combinations = set()

    for item in json_data:
        party_combo = (item['party'], item['effective_party'])
        # Add the tuple to the set only if the two items are different
        if party_combo[0] != party_combo[1]:
            unique_combinations.add(party_combo)

    return unique_combinations


def main():
    # Load environment variables
    load_dotenv()

    # Streamlit UI setup
    st.set_page_config(
        page_icon='🗳️', 
        page_title="EdgeDB", 
        initial_sidebar_state="expanded",
        layout="centered")

    senators_json = load_members_from_files('./data/parliament/senate.json')

    senate_info = extract_info(senators_json)

    #st.write('unique parties:')
    #st.write(senate_info[0])
    #st.write('unique offices:')
    #st.write(senate_info[1])
    
    unique_allegiances = unique_party_combinations(senators_json)
    st.write('unique combinations of party/effective party:')
    st.write(unique_allegiances)


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

    if st.button('add all unique offices'):
        for office in senate_info[1]:
            client.query(
                "insert parliament::Office { name := <str>$office }",
                office=office
            )

    if st.button('add all parties'):
        for party_name in senate_info[0]:
            client.query("""
                insert parliament::Party { 
                name := <str>$name
                }                
            """, name=party_name)

    if st.button('add member info'):
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
            """, 
            full_name=item['name'],
            house=item['house'],
            person_id=item['id'],
            offices=item['offices'],
            electorate=item['electorate'],
            party=item['party']
            )

    # Load senate divisions
    divisions = load_divisions_from_files()
    senate_divisions = {}
    for division_id, division_data in divisions.items():
        if division_data['house'] == 'senate':
            senate_divisions[division_id] = division_data
            
    # st.write(division_data.keys())
    #dict_keys(['id', 'house', 'name', 'date', 'number', 'clock_time', 'aye_votes', 'no_votes', 'possible_turnout', 'rebellions', 'edited', 'summary', 'votes', 'policy_divisions', 'bills'])

    st.write(type(senate_divisions.values()))
    #st.write(senate_divisions.values())
    if st.button('add senate divisions'):
        for item in senate_divisions.values():
            for vote in item['votes']:
                member_id = vote['member']['person']['id']
                print(f"Current member_id: {member_id}")  # Print the current value of member_id

                client.query("""
                    insert parliament::DivisionVote { 
                        division_id := <int16>$division_id,
                        member :=  assert_single((select parliament::Member filter .person_id = <int16>$member_id)),
                        vote := <str>$vote
                    }                
                    """, 
                    division_id=item['id'],
                    member_id=vote['member']['person']['id'],
                    vote=vote['vote'],
                    )

    result = client.query("""
        select parliament::DivisionVote {**} limit 5
    """)

    

    st.json(result)

    # result = client.query_single("""
    #     INSERT parliament::Party {
    #         name := <str>$name,
    #         plotly_col := <str>$plotly_col
    #     }
    # """, name="Australian Labor Party", plotly_col='#E13940')

    #st.write(result)

    

if __name__ == '__main__':
  main()