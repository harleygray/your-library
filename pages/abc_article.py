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
import requests

from unstructured.partition.auto import partition
from unstructured.documents.elements import *
from unstructured.partition.text_type import sentence_count
from unstructured.staging.weaviate import create_unstructured_weaviate_class, stage_for_weaviate
from unstructured.partition.html import partition_html

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


st.header("abc article upload")

# Set up ABCNewsArticle class for Weaviate schema
abc_class = {
    'class': 'ABCNewsArticle',
    'description': 'Class for ABC News articles',
    'properties': [
        {'name': 'text', 'dataType': ['text']},
        {'name': 'category', 'dataType': ['text']},
        {'name': 'article_name', 'dataType': ['text']},
        {'name': 'date', 'dataType': ['text']},
        {'name': 'url', 'dataType': ['text']},
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
        'article_url', 'article_uploader_key']
default_values = [
    None, False, None, None, 
    None, str(uuid.uuid4())]

for key, default_value in zip(keys, default_values):
    if key not in st.session_state:
        st.session_state[key] = default_value



def upload_to_weaviate(data_objects, user_note, user_tags):
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(data_objects):  
            properties = {
                'category': d['category'],
                'text': d['text'],
                'article_name': data_objects[0]['text'],
                'url': st.session_state.article_url,
                'date': date.today().strftime("%Y-%m-%d"),
                'upload_note': user_note,
                'tags': user_tags 
            }
            batch.add_data_object(
                properties,
                'ABCNewsArticle',
                uuid=generate_uuid5(properties),
            )


def reset_initial_state():
    keys = ['data_objects', 'processed', 'document_contents', 'document_name', 
            'article_url', 'article_uploader_key']
    reset_values = [
        None, False, None, None, 
        None, str(uuid.uuid4())]

    for key, reset_value in zip(keys, reset_values):
        st.session_state[key] = reset_value

# Display table when there's data
def document_contents_widget():
    if st.session_state.document_contents is None:
        table_widget.empty() # If there's no data, clear the placeholder
    else:
        table_widget.write(st.session_state.document_contents) # Update the placeholder with a table

# Cached function only runs with a new document upload
@st.cache_data
def process_article(html_content):
    if html_content is None:
        return None
    else:
        # Process document
        doc_elements = partition_html(text=html_content) 
        data_objects = stage_for_weaviate(doc_elements)

        # Create a DataFrame from the data objects
        df = pd.DataFrame({
            'category': [data_object['category'] for data_object in data_objects],
            'text': [data_object['text'] for data_object in data_objects]
        })

        return data_objects, df, data_objects[0]['text']

def on_article_upload():
    article_url = st.session_state.article_url
    if article_url != '':
        html_content = requests.get(article_url).text
        # If multiple files are uploaded, only process the last one
        #if isinstance(uploaded_file, list):
        #    article_url = uploaded_file[-1]
        data_objects, df, document_name = process_article(html_content)

        # Save the results in the session state
        st.session_state.processed = True
        st.session_state.data_objects = data_objects
        st.session_state.document_name = document_name
        st.session_state.document_contents = df



st.session_state.article_url = st.text_input(
    "paste a link to an ABC news article to store its meaning",
    key=st.session_state.article_uploader_key
)
on_article_upload()

reset_button = st.empty()
if st.session_state.data_objects is not None:
    with reset_button:
        if st.button('reset'):
            reset_initial_state()
            st.experimental_rerun()


table_widget = st.empty()
document_contents_widget()

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
                user_note=st.session_state.input_note,
                user_tags=st.session_state.input_tags)
            st.success('document uploaded to library successfully! refreshing page...')
            time.sleep(2)
            # Refresh page ready for another upload
            reset_initial_state()
            st.experimental_rerun()


