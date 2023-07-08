from urllib import parse
import streamlit as st
import helper
from dotenv import load_dotenv
import os
import pandas as pd
import json
from datetime import date

from unstructured.partition.auto import partition
from unstructured.documents.elements import *
from unstructured.partition.text_type import sentence_count
from unstructured.staging.weaviate import create_unstructured_weaviate_class, stage_for_weaviate

import weaviate
from weaviate.util import generate_uuid5
load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

st.title("your library")
#
# need to install pip package to use this 
# st.write(helper.format_for_viewing())


# Set up UnstructuredDocument class for Weaviate schema
unstructured_class = {
    'class': 'UnstructuredDocument',
    'description': 'General class for all documents (todo: add more specific classes)',
    'properties': [
        {'name': 'text', 'dataType': ['text']},
        {'name': 'category', 'dataType': ['text']},
        {'name': 'filename', 'dataType': ['text']},
        {'name': 'file_directory', 'dataType': ['text']},
        {'name': 'date', 'dataType': ['text']},
        {'name': 'filetype', 'dataType': ['text']},
        {'name': 'attached_to_filename', 'dataType': ['text']},
        {'name': 'page_number', 'dataType': ['int']},
        {'name': 'page_name', 'dataType': ['text']},
        {'name': 'url', 'dataType': ['text']},
        {'name': 'sent_from', 'dataType': ['text']},
        {'name': 'sent_to', 'dataType': ['text']},
        {'name': 'subject', 'dataType': ['text']},
        {'name': 'header_footer_type', 'dataType': ['text']},
        {'name': 'text_as_html', 'dataType': ['text']},
        {'name': 'regex_metadata', 'dataType': ['text']},
        {'name': 'tags', 'dataType': ['text']},
        {'name': 'upload_note', 'dataType': ['text']},
    ],
    'vectorizer': 'text2vec-openai', 
    "moduleConfig": {
        "text2vec-openai": {
            "vectorizeClassName": False
        }
    },
}

# Initialize Weaviate client
client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY),
    additional_headers= {
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    }
)

# Test tags
upload_note = "hello weaviate"
tags = "test, weaviate, python"

# store in helper.py
def upload_to_weaviate(data_objects, filename):
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(data_objects):  
            properties = {
                'category': d['category'],
                'text': d['text'],
                'filename': filename,
                'page_number': d['page_number'],
                'filetype': d['filetype'],
                'date': date.today().strftime("%Y-%m-%d"),
                'upload_note': upload_note, # testing
                'tags': tags # testing
            }
            batch.add_data_object(
                properties,
                'UnstructuredDocument',
                uuid=generate_uuid5(properties),
            )

data_objects = None
## Upload any document
raw_document = st.file_uploader("upload any document to store its meaning")
if raw_document is not None:
    st.write("Success: ", raw_document.name," uploaded!")
    doc_elements = partition(file=raw_document)
    data_objects = stage_for_weaviate(doc_elements)
    st.button(label="upload to database",on_click=upload_to_weaviate(data_objects, filename=raw_document.name))  
    #st.write("keys of uploaded doc:", data_objects[0].keys())
    # show to user the text of processed pdf. get confirmation before adding to weaviate
    st.table(pd.DataFrame([data_object['text'] for data_object in data_objects]).iloc[0:10] )
        





# show all items in database
## display a new page














# raw_pdf is now a variable


# set a goal, mindfully
# st.header("Current goal")
# st.text("Assemble the fullstack skeleton")

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

