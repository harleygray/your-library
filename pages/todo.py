import streamlit as st
import pandas as pd
st.set_page_config(
    page_icon='📚', 
    page_title="your library",
    initial_sidebar_state="collapsed")

st.title("to-do list")


# import current file noting metadata.
current_list = pd.read_csv("./data/notes.csv")

# Append new entry to .csv file
def append_to_csv(data):
    with open('./data/notes.csv', 'a') as f:
        f.write('\n' + data)

# user input field to use for appending to .csv file
user_input = st.text_input("add a note to to-do list")

# button to append user input to .csv file
if st.button('add to to-do list'):
    append_to_csv(user_input)
    current_list = pd.read_csv("./data/notes.csv")
    st.success('note added to library successfully!')
    
# CSS to inject contained in a string
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_table_row_index, unsafe_allow_html=True)

# display contents of .csv file
st.table(current_list)