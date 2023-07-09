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


st.set_page_config(
    page_icon='📚', 
    page_title="your library")

st.title("your library")
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


# store in helper.py
def upload_to_weaviate(data_objects, filename, user_note, user_tags):
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(data_objects):  
            properties = {
                'category': d['category'],
                'text': d['text'],
                'filename': filename,
                'page_number': d['page_number'],
                'filetype': d['filetype'],
                'date': date.today().strftime("%Y-%m-%d"),
                'upload_note': user_note,
                'tags': user_tags 
            }
            batch.add_data_object(
                properties,
                'UnstructuredDocument',
                uuid=generate_uuid5(properties),
            )

input_note, input_tags, upload_button = st.empty(), st.empty(), st.empty()
document_contents = st.empty()

# Initialization
if 'data_objects' not in st.session_state:
    st.session_state.data_objects = None

if "processed" not in st.session_state:
    st.session_state.processed = False

if 'input_tags' not in st.session_state:
    st.session_state.input_tags = st.empty()

if 'input_note' not in st.session_state:
    st.session_state.input_note = st.empty()

if 'upload_button' not in st.session_state:
    st.session_state.upload_button = st.empty()

if 'document_contents' not in st.session_state:
    st.session_state.document_contents = st.empty()

if 'document_name' not in st.session_state:
    st.session_state.document_name = None

if 'raw_document' not in st.session_state:
    st.session_state.raw_document = None

if 'content_data' not in st.session_state:
    st.session_state.content_data = None

if 'content_widget' not in st.session_state:
    st.session_state.content_widget = st.empty()


def clear_user_input(input_note, input_tags, upload_button):
    input_note.empty()
    input_tags.empty()
    upload_button.empty()
    st.session_state.input_tags = False
    st.session_state.input_note = False
    st.session_state.upload_button = False


def display_contents(df, table_widget):
    if df is not None and isinstance(df, pd.DataFrame):
        return table_widget.table(df.iloc[0:10])
    elif df is None and not table_widget==st.empty:
        return table_widget.empty()
    elif table_widget==st.empty():
        return table_widget


# cache the function so that this only runs with a new document upload
@st.cache_data
def process_raw_document():
    if 'raw_document' not in st.session_state:
        st.session_state.raw_document = None

    if st.session_state.raw_document is not None:
        # display message that document uploaded and is processing
        status_message = st.empty()
        status_text = st.session_state.raw_document.name +  " uploaded! processing now..."
        status_message.write(status_text)

        # process document
        doc_elements = partition(file=st.session_state.raw_document)
        data_objects = stage_for_weaviate(doc_elements)

        # Save the results in the session state
        st.session_state.processed = True
        st.session_state.data_objects = data_objects
        st.session_state.document_name = st.session_state.raw_document.name
        st.session_state.display_contents = pd.DataFrame({
                'category': [data_object['category'] for data_object in st.session_state.data_objects],
                'text': [data_object['text'] for data_object in st.session_state.data_objects]})
        
        display_contents(
            df = st.session_state.content_data,
            table_widget = document_contents
        )

        
        status_message.empty()

    

st.file_uploader(
    "upload any document to store its meaning", 
    key="raw_document",
    on_change=process_raw_document
)

document_contents = st.empty()
display_contents(
    df = st.session_state.content_data,
    table_widget = document_contents
)
# function to process document and display contents
if st.session_state.raw_document is not None:
    status_message = st.empty()
    status_text = st.session_state.raw_document.name +  " uploaded! processing now..."
    status_message.write(status_text)
    doc_elements = partition(file=st.session_state.raw_document)
    data_objects = stage_for_weaviate(doc_elements)
    # Save the results in the session state
    st.session_state.processed = True
    st.session_state.data_objects = data_objects
    st.session_state.document_name = st.session_state.raw_document.name
    st.session_state.document_contents = pd.DataFrame({
    'category': [data_object['category'] for data_object in st.session_state.data_objects],
    'text': [data_object['text'] for data_object in st.session_state.data_objects]
    })
    status_message.empty()

    
    if st.session_state.document_contents is not None and isinstance(st.session_state.document_contents, pd.DataFrame):
        st.table(st.session_state.document_contents.iloc[0:10])



if st.session_state.processed:
    status_message = st.empty()
    status_text = st.session_state.document_name +  " processed! add notes or tags, then upload to library"
    status_message.write(status_text)

    # display on same line
    input_note, input_tags, upload_button = st.columns(3)
    st.session_state.input_note = True
    st.session_state.input_tags = True
    st.session_state.upload_button = True

# input field for user to add notes to document
if st.session_state.input_note is True and st.session_state.processed:
    with input_note:
        st.session_state.input_note = st.text_input("document notes")
        

# input field for user to add tags to document
if st.session_state.input_tags is True and st.session_state.processed:
    with input_tags:
        st.session_state.input_tags = st.text_input("tags")

# button to upload the cleaned document to Weaviate
if st.session_state.upload_button is True and st.session_state.processed:
    with upload_button:
        if st.button('     upload to library'):
            upload_to_weaviate(
                st.session_state['data_objects'], 
                filename=st.session_state.raw_document.name,
                user_note=st.session_state.input_note,
                user_tags=st.session_state.input_tags)
            clear_user_input(input_note, input_tags, upload_button)
            status_message = st.empty()
            # set raw_document, data_objects, df, tags, and user_note to None
            raw_document = None
            st.session_state.data_objects = None
            
            
            st.session_state.df = None

            st.session_state.processed = False
            st.session_state.document_contents = None
            st.success('document uploaded to library successfully!')




    

# once document is uploaded or changed, process it and display the contents
# if st.session_state.raw_document is not None:
#     process_document()
#     st.table(st.session_state.document_contents.iloc[0:10])











# import current file noting metadata.
current_list = pd.read_csv("./data/notes.csv")

# function to append new entry to .csv file
def append_to_csv(data):
    with open('./data/notes.csv', 'a') as f:
        f.write('\n' + data)

# user input field to use for appending to .csv file
user_input = st.text_input("add a note to your library")

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



# use Unstructured to extract meaning and prepare for embedding


# embed in weaviate using the module. 

