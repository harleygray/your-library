import edgedb
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from itertools import groupby
from operator import attrgetter

@st.cache_data
def return_divisions(_client, selected_member_names, selected_division_category):
    query = """
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
        filter .division_category = <str>$selected_division_category"""

    divisions = _client.query(query, selected_member_names=selected_member_names, selected_division_category=selected_division_category)
    
    # Flatten the data
    flattened_data = [
        {
            "division_name": obj.division_name,
            "member_name": vote.member_name,
            "vote": str(vote.vote),
        }
        for obj in divisions
        for vote in obj.member_votes
    ]

    # Create a DataFrame
    df = pd.DataFrame(flattened_data)
    return df

@st.cache_data
def query_member_records(_client, input_postcode):
    query = """
        SELECT parliament::Member {
            full_name,
            party_name := .party.name,
            house,
            votes: {
                division: {
                name,
                summary,
                division_category
                },
                vote
            },
            electorates: {
                name,
                suburbs: {
                name,
                postcode
                } FILTER .postcode = <str>$input_postcode
            } FILTER .suburbs.postcode = <str>$input_postcode
        } FILTER .electorates.suburbs.postcode = <str>$input_postcode;
        """
    members = _client.query(query, input_postcode=str(input_postcode))

    # Flatten the data
    flattened_data = [
        {
            "member_name": obj.full_name,
            "party": obj.party_name,
            "house": str(obj.house),
            "division_name": vote.division.name,
            "vote": str(vote.vote),
            "category": vote.division.division_category,
        }
        for obj in members
        for vote in obj.votes
    ]

    # Create a DataFrame
    df = pd.DataFrame(flattened_data)
    return df


def main():
    # Load environment variables
    load_dotenv()
    EDGEDB_INSTANCE = os.getenv("EDGEDB_INSTANCE")
    EDGEDB_SECRET_KEY = os.getenv("EDGEDB_SECRET_KEY")
    
    # Streamlit UI setup
    st.set_page_config(
        page_icon='🗳️', 
        page_title="EdgeDB", 
        initial_sidebar_state="expanded",
        layout="centered")

    # EdgeDB client
    client = edgedb.create_client()



    # with st.expander('select all divisions a member voted in'):
    #     all_members = client.query("""
    #         select distinct(parliament::Member {
    #             full_name,
    #             party: { name }
    #         })""")
        
    #     member_names = map(lambda category: category.full_name + ", " + category.party.name, all_members)

    #     # Sort all_members by party.name
    #     all_members_sorted = sorted(all_members, key=attrgetter('party.name'))

    #     # Group members by party.name
    #     grouped_members = groupby(all_members_sorted, key=attrgetter('party.name'))

    #     # grouped_members is an iterable of tuples, where the first element is the party name,
    #     # and the second element is an iterable of members in that party.
    #     # Convert it to a dictionary where the party name is the key and the value is a list of member names:
    #     member_names_by_party = {party: list(map(attrgetter('full_name'), members)) for party, members in grouped_members}
        
    #     member_col, party_col = st.columns(2)
    #     with party_col: 
    #         selected_party = st.multiselect(label='(optional) filter member list by party', default="Australian Labor Party", options=list(member_names_by_party.keys()))

    #     if selected_party:  
    #         party_members_options = [member for party in selected_party for member in member_names_by_party.get(party, [])]
    #     else:
    #         # If no party is selected, show all members
    #         party_members_options = [member for members in member_names_by_party.values() for member in members]

    #     with member_col:
    #         selected_member_names = st.multiselect(label='members to inspect', default="Anthony Albanese", options=party_members_options)

    #     divisions = return_divisions(client, selected_member_names=selected_member_names, selected_division_category=selected_division_category)


    #     # Pivot the DataFrame to get one column per member
    #     pivot_df = divisions.pivot_table(index="division_name", columns="member_name", values="vote", aggfunc='first')
        
    #     st.dataframe(pivot_df)

    
    
    # Select one division at random
    random_state = 0
    with st.form(key='random_division'):
        # Return the voting records of all members representing the postcode
        input_postcode = st.number_input('enter your postcode', min_value=0, max_value=7999, value=4000)
        member_records = query_member_records(client, input_postcode=input_postcode)

        # Filter by house
        selected_house = st.radio("choose house", options=["representatives","senate"])

        # Filter by division_category
        division_categories = client.query("select distinct(parliament::Division.division_category);")
        selected_division_category =  st.radio(label='filter by type of division', options=list(division_categories))

        # Filter the DataFrame by selected house and selected division category
        filtered_records = member_records.loc[
            (member_records["house"] == selected_house) & 
            (member_records["category"] == selected_division_category)
        ]
        
        st.write(filtered_records.sample(n=1))
        st.form_submit_button(label='new random division')

    
    
    # Pivot the DataFrame to get one column per member
    #pivot_df = df.pivot_table(index="division_name", columns="member_name", values="vote", aggfunc='first')
    
    #st.dataframe(pivot_df)

    


if __name__ == '__main__':
  main()