from urllib import parse
import streamlit as st
import helper
import pandas as pd
import numpy as np


st.title("your library")
st.markdown("upload a pdf document to store its meaning")
raw_pdf = st.file_uploader("",type=["pdf"])
if raw_pdf is not None:
    st.write("Success: ", raw_pdf.name," uploaded!")
    parsed_pdf = helper.parse_pdf(raw_pdf, user_input="")
    parsed_pdf = pd.read_csv("./data/parsed_pdf.csv")
    # show to user the processed pdf. get confirmation before adding to weaviate
    st.table(parsed_pdf)
    st.button(label="upload to database",on_click=helper.send_to_weaviate(parsed_pdf))
    
# show all items in database
## display a new page





# raw_pdf is now a variable


# set a goal, mindfully
st.header("Current goal")
st.text("Assemble the fullstack skeleton")

# add new note
user_input = st.text_input("add new note")
if user_input is not None:
    st.write('User input: ', user_input)




# import current file noting metadata.
current_list = pd.read_csv("./data/notes.csv")

# function to append new entry to .csv file






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



# use Unstructured to extract meaning and prepare for embedding


# embed in weaviate using the module. 

