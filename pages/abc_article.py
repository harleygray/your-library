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
        {'name': 'author_list', 'dataType': ['text']}, #
        {'name': 'publisher', 'dataType': ['text']}, #
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
        'article_url', 'article_uploader_key', 'data_editor']
default_values = [
    None, False, None, None, 
    None, str(uuid.uuid4())]

for key, default_value in zip(keys, default_values):
    if key not in st.session_state:
        st.session_state[key] = default_value

def cleanse_data(data_objects):
    # Identify article name and change its category
    data_objects[0]['category'] = 'ArticleName'

    # Identify authors and change category
    # Iterate over the data_objects list
    for item in data_objects:
        # Check if the category of the current item is 'Title' and the text starts with 'By '
        if item['category'] == 'Title' and item['text'].startswith('By '):
            # If it is, change the category to 'AuthorList' and remove 'By ' from the text
            item['category'] = 'AuthorList'
            item['text'] = item['text'][3:]  # Remove 'By ' from the start of the text
            # If there are exactly two authors (i.e., there is no comma and there is ' and' in the text)
            if ',' not in item['text'] and ' and' in item['text']:
                # Replace ' and' with ', '
                item['text'] = item['text'].replace(' and', ',')
            else:
                # If ' and' is in the text, remove it
                item['text'] = item['text'].replace(' and', '').strip()
            break


    # Find the key points and assign to category 'KeyPoint'
    # Define the start of the pattern
    start_pattern = {"category": "Title", "text": "Key points:"}

    # Iterate over the data_objects list
    i = 0
    while i < len(data_objects):
        # Check if the current element's 'category' and 'text' match those in the start pattern
        if data_objects[i].get('category') == start_pattern['category'] and data_objects[i].get('text') == start_pattern['text']:
            # If the start of the pattern is matched, remove this element
            del data_objects[i]
            # Then change the category of the following 'ListItem' elements to 'KeyPoint'
            while i < len(data_objects) and data_objects[i]["category"] == "ListItem":
                data_objects[i]["category"] = "KeyPoint"
                i += 1
        else:
            i += 1


    # Remove the 'Read more' section
    # Define the start of the sequence
    start_sequence = {"category": "Title", "text": "Read more about the Indigenous Voice to Parliament:"}

    # Iterate over the data_objects list
    i = 0
    while i < len(data_objects):
        # Check if the current element's 'category' and 'text' match those in the start sequence
        if data_objects[i].get('category') == start_sequence['category'] and data_objects[i].get('text') == start_sequence['text']:
            # If the start of the sequence is matched, remove this element
            del data_objects[i]
            # Then remove the following 'ListItem' elements
            while i < len(data_objects) and data_objects[i]["category"] == "ListItem":
                del data_objects[i]
        else:
            i += 1

    # Remove elements matching the pattern "Title: Loading..."
    # Define the pattern to remove
    remove_pattern = {"category": "Title", "text": "Loading..."}

    # Filter out the elements that match the remove pattern
    data_objects = [d for d in data_objects if not (d.get('category') == remove_pattern['category'] and d.get('text') == remove_pattern['text'])]


    # Remove rows matching the pattern "ABC " at the beginning and ")" at the end
    #data_objects = [
    #    item for item in data_objects if 
    #    not (item['text'].startswith('ABC ') and item['text'].endswith(')') and '(' not in item['text'])
    #]

    # Cut off after "NarrativeText: If you're ..."
    # Define the pattern to stop at
    stop_pattern = {"category": "NarrativeText", "text": "If you're unable to load the form, you can access it here."}

    # Find the index of the element with the stop pattern
    stop_index = next((i for i, d in enumerate(data_objects) if d.get('category') == stop_pattern['category'] and d.get('text') == stop_pattern['text']), None)

    # If the stop pattern was found, slice the list up to that index
    if stop_index is not None:
        data_objects = data_objects[:stop_index]

    # Cut off after "NarrativeText: If you're ..."
    # Define the pattern to stop at
    stop_pattern = {"category": "Title", "text": "Share"}

    # Find the index of the element with the stop pattern
    stop_index = next((i for i, d in enumerate(data_objects) if d.get('category') == stop_pattern['category'] and d.get('text') == stop_pattern['text']), None)

    # If the stop pattern was found, slice the list up to that index
    if stop_index is not None:
        data_objects = data_objects[:stop_index]



    # Identify publishing outlet
    # Iterate over the data_objects list
    for item in data_objects:
        # Check if the category of the current item is 'Title' and the text starts with 'ABC '
        if item['category'] == 'Title' and item['text'].startswith('ABC '):
            # If it is, change the category to 'PublishingOutlet' and keep the text as it is
            item['category'] = 'PublishingOutlet'
            break


    # Remove fluff at start of article
    # Remove rows matching the pattern "ABC " at the beginning and ")" at the end
    data_objects = [
        item for item in data_objects if not (
            item['text'] == 'updated' or
            item['text'] == 'Copy link' or
            item['text'] == 'Posted' or
            item['text'] == 'Help keep family & friends informed by sharing this article' or
            item['text'] == 'Link copied' or
            item['text'].startswith('abc.net.au') or 
            (item['text'].startswith('ABC ') and item['text'].endswith(')') and '(' not in item['text']) or
            (item['text'].startswith('Supplied: ') and item['text'].endswith(')') and '(' not in item['text'])
        )
    ]

    return data_objects


def upload_to_weaviate(data_objects, user_note, user_tags):
    article_name = next((data_object['text'] for data_object in data_objects if data_object['category'] == 'ArticleName'), None)
    author_list = next((data_object['text'] for data_object in data_objects if data_object['category'] == 'AuthorList'), None)
    publisher = next((data_object['text'] for data_object in data_objects if data_object['category'] == 'PublishingOutlet'), None)


    # Remove the 'AuthorList' and 'PublishingOutlet' data objects
    data_objects = [data_object for data_object in data_objects if data_object['category'] not in ['ArticleName', 'AuthorList', 'PublishingOutlet']]
    print("article name: ", article_name)
    print("author list: ", author_list)
    print("publisher: ", publisher)
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(data_objects):  
            properties = {
                'category': d['category'],
                'text': d['text'],
                'article_name': article_name,
                'url': st.session_state.article_url,
                'author_list': author_list,
                'publisher': publisher,
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
            'article_url', 'article_uploader_key', 'data_editor']
    reset_values = [
        None, False, None, None, 
        None, str(uuid.uuid4())]

    for key, reset_value in zip(keys, reset_values):
        st.session_state[key] = reset_value

# Display table when there's data
def document_contents_widget():
    if st.session_state.data_objects is None:
        table_widget.empty() # If there's no data, clear the placeholder
    else:
        st.data_editor(
            # show only the text and category columns
            st.session_state.data_objects, key="data_editor")

# Cached function only runs with a new document upload
@st.cache_data
def process_article(html_content):
    if html_content is None:
        return None
    else:
        # Process document
        doc_elements = partition_html(text=html_content) 
        data_objects = stage_for_weaviate(doc_elements)

        # Cleanse data
        data_objects = cleanse_data(data_objects)

        # List of columns to remove
        columns_to_remove = ["filetype", "page_number"]

        # Remove the columns
        data_objects = [
            {key: value for key, value in obj.items() if key not in columns_to_remove}
            for obj in data_objects
        ]

        # Create a new list of dictionaries with the keys in the order you want
        data_objects = [{key: obj[key] for key in ["category", "text"]} for obj in data_objects]
        return data_objects, data_objects[0]['text']

def on_article_upload():
    article_url = st.session_state.article_url
    if article_url != '':
        html_content = requests.get(article_url).text
        # If multiple files are uploaded, only process the last one
        #if isinstance(uploaded_file, list):
        #    article_url = uploaded_file[-1]
        data_objects, document_name = process_article(html_content)

        # Save the results in the session state
        st.session_state.processed = True
        st.session_state.data_objects = data_objects
        st.session_state.document_name = document_name



st.session_state.article_url = st.text_input(
    "paste a link to an ABC news article to store its meaning"
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
cleanse_data_button = st.empty()
st.write(st.session_state.data_editor)
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
            if st.session_state.data_editor['edited_rows']:
                # If it isn't, iterate over the 'edited_rows'
                for row_index, changes in st.session_state.data_editor['edited_rows'].items():
                    # Convert the row index to an integer
                    row_index = int(row_index)
                    # Update the corresponding row in 'data_objects' with the changes
                    for column, new_value in changes.items():
                        st.session_state.data_objects[row_index][column] = new_value
            upload_to_weaviate(
                st.session_state.data_objects, 
                user_note=st.session_state.input_note,
                user_tags=st.session_state.input_tags)
            st.success('document uploaded to library successfully! refreshing page...')
            time.sleep(2)
            # Refresh page ready for another upload
            reset_initial_state()
            st.experimental_rerun()


