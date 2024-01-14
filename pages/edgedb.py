import edgedb
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from itertools import groupby
from operator import attrgetter

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

    with st.sidebar:
        selected_house = st.radio("choose house (WIP)", options=["representatives","senate"])

        division_categories = client.query("select distinct(parliament::Division.division_category);")
        selected_division_category =  st.radio(label='filter by type of division', options=list(division_categories))

    with st.expander('select all divisions a member voted in'):
        all_members = client.query("""
            select distinct(parliament::Member {
                full_name,
                party: { name }
            })""")
        
        member_names = map(lambda category: category.full_name + ", " + category.party.name, all_members)

        # Sort all_members by party.name
        all_members_sorted = sorted(all_members, key=attrgetter('party.name'))

        # Group members by party.name
        grouped_members = groupby(all_members_sorted, key=attrgetter('party.name'))

        # grouped_members is an iterable of tuples, where the first element is the party name,
        # and the second element is an iterable of members in that party.
        # Convert it to a dictionary where the party name is the key and the value is a list of member names:
        member_names_by_party = {party: list(map(attrgetter('full_name'), members)) for party, members in grouped_members}
        
        member_col, party_col = st.columns(2)
        with party_col: 
            selected_party = st.multiselect(label='(optional) filter member list by party', default="Australian Labor Party", options=list(member_names_by_party.keys()))

        if selected_party:  
            party_members_options = [member for party in selected_party for member in member_names_by_party.get(party, [])]
        else:
            # If no party is selected, show all members
            party_members_options = [member for members in member_names_by_party.values() for member in members]

        with member_col:
            selected_member_names = st.multiselect(label='members to inspect', default="Anthony Albanese", options=party_members_options)

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
        divisions = client.query(query, selected_member_names=selected_member_names, selected_division_category=selected_division_category)

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

        # Pivot the DataFrame to get one column per member
        pivot_df = df.pivot_table(index="division_name", columns="member_name", values="vote", aggfunc='first')
        
        st.dataframe(pivot_df)


    input_postcode = st.number_input('enter your postcode', min_value=0, max_value=7999, value=4000)

    
    query = """
        SELECT parliament::Member {
            full_name,
            party_name := .party.name,
            house,
            votes: {
                division: {
                name,
                summary
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
    members = client.query(query, input_postcode=str(input_postcode))

    # Flatten the data
    flattened_data = [
        {
            "member_name": obj.full_name,
            "party": obj.party_name,
            "house": str(obj.house),
            "division_name": vote.division.name,
            "vote": str(vote.vote),
        }
        for obj in members
        for vote in obj.votes
    ]

    # Create a DataFrame
    df = pd.DataFrame(flattened_data)

    # Pivot the DataFrame to get one column per member
    pivot_df = df.pivot_table(index="division_name", columns="member_name", values="vote", aggfunc='first')
    
    st.dataframe(pivot_df)



if __name__ == '__main__':
  main()