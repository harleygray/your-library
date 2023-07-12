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
st.set_page_config(
    page_icon='📚', 
    page_title="your library",
    initial_sidebar_state="collapsed")
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
st.write("For now only the ABCNewsArticle class is available")
selected_class = st.selectbox('Select a class', ["ABCNewsArticle"])

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

def reset_results():
    st.session_state['results'] = []

# show objects of the matching tag and class close to a similarity search
st.write("show objects of the matching tag and class close to a similarity search")
# user input for concepts, comma separated
concepts_input = st.text_input("enter search query", "cost of living")
concepts = concepts_input.split(", ")
max_distance = 0.3
nearText = {
    "concepts": concepts,
    "distance": max_distance}

search_button = st.empty()
result_limit = st.slider("result limit", 1, 10, 4)
results_table = st.empty()

with search_button:
    if st.button("search"):
        reset_results()
        response = (
            client.query  # start a new query
            .get("ABCNewsArticle", ["text", "article_name", "upload_note", "tags"])  
            .with_near_text(nearText)  
            .with_limit(result_limit) 
            .with_where({
                "path": ["category"],
                "operator": "Equal",
                "valueString": "NarrativeText"
            })
            .do() 
        )
        # show the objects with the selected tag
        for obj in response['data']['Get'][selected_class]:
            if 'tags' in obj:
                if selected_tag in obj['tags']:
                    st.session_state['results'].append(obj)

        df = pd.DataFrame(st.session_state['results'])
        # add a relevance score column
        df['relevance_score'] = df.index + 1
        # define a custom aggregation function
        def aggregate_texts(series):
            return '\n'.join(f"{i+1}. {text}" for i, text in enumerate(series))

        # group by tags, input notes, and article names, and aggregate the text
        grouped_df = df.groupby(['tags', 'upload_note', 'article_name'])['text'].agg(aggregate_texts).reset_index()
        
        
        
        for _, group in grouped_df.groupby(['tags', 'upload_note', 'article_name']):
            # Create a markdown string for the group header
            group_header = f"**Tags:** {group['tags'].iloc[0]}  \n**Upload Note:** {group['upload_note'].iloc[0]}  \n**Article Name:** {group['article_name'].iloc[0]}"
            st.write(group_header)
            
            # Create a markdown string for the ordered list of texts
            text_list = "\n".join(f"{text}" for text in group['text'])
            st.markdown(text_list)



st.button(
    label="fetch from library",
    on_click=helper.fetch_from_weaviate(
        helper.format_graphql_query("test")))

# unsure here of how i get the response into a table


st.button(
    label="generate summaries (not working yet)" 
)

#formatted_graphql_response = helper.format_for_viewing(graphql_response)
# st.table(graphql_response)



