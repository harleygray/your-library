import streamlit as st
import pandas as pd
import helper
import weaviate
from dotenv import load_dotenv
import os
load_dotenv()


WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

st.header("current library contents")
show_library = False


# url to embed into personal library
# https://towardsdatascience.com/a-multi-page-interactive-dashboard-with-streamlit-and-plotly-c3182443871a



# Drop down streamlit component to select available classes
# st.selectbox(
#     label="select class",

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY),
    additional_headers= {
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    }
)

schema = client.schema.get()
# Get class list from schema
class_list = [class_dict['class'] for class_dict in schema['classes']]

selected_class = st.selectbox('Select a class', class_list)

# Now you can use selected_class in your application logic
st.write(f"You selected {selected_class}")

# Query Weaviate to get the data objects in the selected class
objects = (
    client.query
    .get(selected_class, ["tags", "text", "article_name", "date", "url", "upload_note"])
    .with_where({
        "path": ["category"],
        "operator": "Equal",
        "valueString": "NarrativeText"
    })
    .do()
)

st.write(objects)

# Extract the unique tags values
tags = set()
for obj in objects['data']['Get'][selected_class]:
    if 'tags' in obj:
        # Split the tags string into individual tags
        individual_tags = obj['tags'].split(', ')
        # Add each tag to the set
        tags.update(individual_tags)

# Create a dropdown selector for the tags
selected_tag = st.selectbox('Select a tag', list(tags))


# show the objects with the selected tag
for obj in objects['data']['Get'][selected_class]:
    if 'tags' in obj:
        if selected_tag in obj['tags']:
            st.write(obj)



st.button(
    label="fetch from library",
    on_click=helper.fetch_from_weaviate(
        helper.format_graphql_query("test")))

# unsure here of how i get the response into a table

st.table(pd.read_csv("data/parsed_pdf.csv"))
graphql_response = ""

st.button(
    label="generate summaries",
    on_click=helper.summarise_embeds(graphql_response) # changes graphql_response
)

#formatted_graphql_response = helper.format_for_viewing(graphql_response)
# st.table(graphql_response)



