from urllib import parse
import streamlit as st
import helper
from dotenv import load_dotenv
import os
import pandas as pd
import json
from datetime import date
import uuid
import time

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
    page_title="your library",
    initial_sidebar_state="collapsed")


st.header("document upload")

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

# Set initial state
keys = ['data_objects', 'processed', 'document_contents', 'document_name', 
        'raw_document', 'file_uploader_key']
default_values = [
    None, False, None, None, 
    None, str(uuid.uuid4())]

for key, default_value in zip(keys, default_values):
    if key not in st.session_state:
        st.session_state[key] = default_value



def upload_to_weaviate(data_objects, filename, user_note, user_tags):
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(data_objects):  
            properties = {
                'category': d['category'],
                'text': d['text'],
                'filename': filename,
                #'page_number': d['page_number'],
                #'filetype': d['filetype'],
                'date': date.today().strftime("%Y-%m-%d"),
                'upload_note': user_note,
                'tags': user_tags 
            }
            batch.add_data_object(
                properties,
                'UnstructuredDocument',
                uuid=generate_uuid5(properties),
            )


def reset_initial_state():
    keys = ['data_objects', 'processed', 'document_contents', 'document_name', 
            'raw_document', 'file_uploader_key']
    reset_values = [
        None, False, None, None, 
        None, str(uuid.uuid4())]

    for key, reset_value in zip(keys, reset_values):
        st.session_state[key] = reset_value

# Display table when there's data
#def document_contents_widget():
#    if st.session_state.document_contents is None:
#        table_widget.empty() # If there's no data, clear the placeholder
#    else:
#        table_widget.write(st.session_state.document_contents) # Update the placeholder with a table

# Cached function only runs with a new document upload
@st.cache_data
def process_raw_document(raw_document):
    if raw_document is None:
        return None
    else:
        # Process document
        doc_elements = partition(file=raw_document)
        data_objects = stage_for_weaviate(doc_elements)

        # Create a DataFrame from the data objects
        df = pd.DataFrame({
            'category': [data_object['category'] for data_object in data_objects],
            'text': [data_object['text'] for data_object in data_objects],
            'to remove': False
        })

        return data_objects, df, raw_document.name

def on_file_upload():
    uploaded_file = st.session_state.raw_document
    if uploaded_file is not None:
        # If multiple files are uploaded, only process the last one
        if isinstance(uploaded_file, list):
            uploaded_file = uploaded_file[-1]
        data_objects, df, document_name = process_raw_document(uploaded_file)

        # Save the results in the session state
        st.session_state.processed = True
        st.session_state.data_objects = data_objects
        st.session_state.document_name = document_name
        st.session_state.document_contents = df



st.session_state.raw_document = st.file_uploader(
    "upload any document to store its meaning",
    key=st.session_state.file_uploader_key
)
on_file_upload()

reset_button = st.empty()
if st.session_state.raw_document is not None:
    with reset_button:
        if st.button('reset'):
            reset_initial_state()
            st.experimental_rerun()


table_widget = st.empty()
# Display table when there's data
if st.session_state.document_contents is None:
    table_widget.empty() # If there's no data, clear the placeholder
else:
    table_widget.data_editor(
        st.session_state.document_contents, 
        column_config={
            "to remove": st.column_config.CheckboxColumn(
                "Remove?",
                help="Tick this box to remove the row from the upload"
            )},
        key="data_editor",
        hide_index=True)

    if st.session_state.data_editor['edited_rows']:
        # If it isn't, iterate over the 'edited_rows'
        for row_index, changes in st.session_state.data_editor['edited_rows'].items():
            # Convert the row index to an integer
            row_index = int(row_index)
            # Update the corresponding row in 'document_contents' with the changes
            for column, new_value in changes.items():
                st.session_state.document_contents.loc[row_index,column] = new_value

        # Create a mask that identifies which rows are NOT marked for removal
        mask = st.session_state.document_contents['to remove'] == False

        # Filter the rows in document_contents using the mask
        filtered_document_contents = st.session_state.document_contents[mask]

        # Initialize an empty list to store the data objects
        data_objects = []

        # Iterate through the rows of the filtered DataFrame
        for _, row in filtered_document_contents.iterrows():
            # Create a dictionary for each row, using the column names as keys
            data_object = {
                "text": row["text"],
                "category": row["category"]
            }
            
            # Append the dictionary to the list of data objects
            data_objects.append(data_object)

        # Display the data objects
        st.write(data_objects)

        # Optionally, update the session_state with the new data_objects list
        st.session_state.data_objects = data_objects

        # At this point, data_objects is a list of dictionaries, each representing a row of filtered_document_contents



# Show document contents with removed rows

st.header("Document contents with edits and rows removed")
st.dataframe(pd.DataFrame(
    {
        'category': [data_object['category'] for data_object in st.session_state.data_objects],
        'text': [data_object['text'] for data_object in st.session_state.data_objects]
    }), 
    hide_index=True)


st.write(st.session_state.data_objects)
input_note, input_tags, upload_button = st.empty(), st.empty(), st.empty()
# Once a document is ready for upload, display a message and input fields
if st.session_state.processed:
    # Status message
    status_message = st.empty()
    status_text = "`{0}` processed! add notes or tags, then upload to library".format(st.session_state.document_name)
    status_message.write(status_text)

    # User input and upload button
    input_note, input_tags, upload_button = st.columns(3)
    with input_note:
        st.session_state.input_note = st.text_input("document notes")
    with input_tags:
        st.session_state.input_tags = st.text_input("tags")
    with upload_button:
        if st.button('     upload to library'):
            upload_to_weaviate(
                st.session_state.data_objects, 
                filename=st.session_state.raw_document.name,
                user_note=st.session_state.input_note,
                user_tags=st.session_state.input_tags)
            st.success('document uploaded to library successfully! refreshing page...')
            time.sleep(2)
            # Refresh page ready for another upload
            reset_initial_state()
            st.experimental_rerun()


