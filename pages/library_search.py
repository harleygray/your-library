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

st.header("library search")
st.write("search the contents of your library via semantic search")

# url to embed into personal library
# https://towardsdatascience.com/a-multi-page-interactive-dashboard-with-streamlit-and-plotly-c3182443871a

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY),
    additional_headers= {
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    }
)


# Set initial state
keys = [
    'selected_tag', 'selected_class', 'concepts_input', 'result_limit', 'results',
    'results_table'
]
default_values = [
    None, None, None, None, None, pd.DataFrame(columns=['group_header', 'text_list'])]
for key, default_value in zip(keys, default_values):
    if key not in st.session_state:
        st.session_state[key] = default_value



# Get class list from schema
schema = client.schema.get()
class_list = [class_dict['class'] for class_dict in schema['classes']]

selected_class, selected_tag = st.columns(2)


with selected_class:
    st.session_state.selected_class = st.selectbox('select a class (only ABCNewsArticle is available currently)', ["ABCNewsArticle"])



import pandas as pd
import os

# Define the path to the .csv file
csv_path = "./data/ABC_tags.csv"

# Function to run the query and update the .csv file
def update_csv():
    # Initialize an empty set to store the unique tags
    tags = set()

    # Initialize the pagination offset
    offset = 0

    # Set the number of objects to retrieve per query
    limit = 100

    # Continue querying until no more objects are returned
    while True:
        # Query Weaviate to get the data objects in the selected class
        objects = (
            client.query
            .get(
                st.session_state.selected_class, 
                ["tags", "text", "article_name", "date", "url", "upload_note"])
            .with_where({
                "path": ["category"],
                "operator": "Equal",
                "valueString": "NarrativeText"
            })
            .with_limit(limit)
            .with_offset(offset)
            .do()
        )

        # Break the loop if no objects are returned
        if not objects['data']['Get'][st.session_state.selected_class]:
            break

        # Extract the unique tags values
        for obj in objects['data']['Get'][st.session_state.selected_class]:
            if 'tags' in obj:
                # Check if tags is a list
                if isinstance(obj['tags'], list):
                    # If it's a list, add each tag to the set
                    tags.update(obj['tags'])
                elif isinstance(obj['tags'], str):
                    # If it's a string, split it into individual tags and add them to the set
                    individual_tags = obj['tags'].split(', ')
                    tags.update(individual_tags)

        # Increase the offset for the next query
        offset += limit

    # Save the unique tags to a .csv file
    pd.DataFrame(list(tags), columns=['Tags']).to_csv(csv_path, index=False)

# Button to run the query and update the .csv file
if st.button('Update Tags'):
    update_csv()

# Read the dropdown selector list from the .csv file
if os.path.exists(csv_path):
    tags = pd.read_csv(csv_path)['Tags'].tolist()
    # Create a dropdown selector for the tags
    with selected_tag:
        st.session_state.selected_tag = st.selectbox('Select a tag', tags)


def reset_results():
    st.session_state['results'] = []
    st.session_state['results_table'] = pd.DataFrame(columns=['group_header', 'text_list'])

concepts_input, result_limit = st.columns(2)

# User input for concepts, comma separated
with concepts_input:
    st.session_state.concepts_input = st.text_input("enter search query to use for similarity search", "indigenous recognition").split(", ")
with result_limit:
    st.session_state.result_limit = st.slider("result limit", 1, 10, 4)

max_distance = 0.3
nearText = {
    "concepts": st.session_state.concepts_input,
    "distance": max_distance}

search_button = st.empty()

results_table = st.empty()

with search_button:
    if st.button("search"):
        reset_results()
        response = (
            client.query  # start a new query
            .get("ABCNewsArticle", ["text", "article_name", "url", "upload_note", "tags"])  
            .with_near_text(nearText)  
            .with_limit(st.session_state.result_limit) 
            .with_where({
                "path": ["category"],
                "operator": "Equal",
                "valueString": "NarrativeText"
            })
            .do() 
        )
        # show the objects with the selected tag
        for obj in response['data']['Get'][st.session_state.selected_class]:
            if 'tags' in obj:
                if st.session_state.selected_tag in obj['tags']:
                    st.session_state['results'].append(obj)

        df = pd.DataFrame(st.session_state['results'])
        # add a relevance score column
        df['relevance_score'] = df.index + 1
        # define a custom aggregation function
        def aggregate_texts(series):
            return '\n'.join(f"{i+1}. {text}" for i, text in enumerate(series))

        if df.empty:
            group_header = f"No results found in library similar to `{st.session_state.concepts_input}`"
            text_list = ""
            results_df = pd.concat([st.session_state.results_table, pd.DataFrame([{'group_header': group_header, 'text_list': text_list}])], ignore_index=True)
            # Save the results DataFrame to the Streamlit session state
            st.session_state.results_table = results_df
        else:
            # group by tags, input notes, and article names, and aggregate the text
            grouped_df = df.groupby(['tags', 'upload_note', 'url', 'article_name'])['text'].agg(aggregate_texts).reset_index()
            results_df = st.session_state.results_table
            
            for _, group in grouped_df.groupby(['tags', 'upload_note', 'url', 'article_name']):
                # Create a markdown string for the group header
                group_header = f"`Article Name: ` {group['article_name'].iloc[0]}   \n`URL: ` {group['url'].iloc[0]}  \n`Tags: ` {group['tags'].iloc[0]}  \n`Upload Note: ` {group['upload_note'].iloc[0]}"
                # Create a markdown string for the ordered list of texts
                text_list = "\n".join(f"{text}" for text in group['text'])
                # Append the group header and text list to the results DataFrame
                results_df = pd.concat([results_df, pd.DataFrame([{'group_header': group_header, 'text_list': text_list}])], ignore_index=True)
                 # Save the results DataFrame to the Streamlit session state
                st.session_state.results_table = results_df

        
       

for i in range(len(st.session_state.results_table)):
    st.markdown(st.session_state.results_table['group_header'][i])
    st.markdown(st.session_state.results_table['text_list'][i])



st.button(
    label="generate summaries (not working yet)" 
)


