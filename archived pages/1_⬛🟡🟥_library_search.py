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
st.write("on October 14, every Australian citizen will vote on the following question:")
st.markdown("""
>A Proposed Law: to alter the Constitution to recognise the First Peoples of Australia by establishing an Aboriginal and Torres Strait Islander Voice.
>
>Do you approve this proposed alteration?
""")

st.markdown("""
The Voice would be an independent, representative body for First Nations peoples. 

- It would advise the Australian Parliament and the Government.
- It would give First Nations peoples a say on matters that affect them.

[source](https://voice.gov.au/resources/fact-sheet-referendum-question-and-constitutional-amendment)
""")


client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY),
    additional_headers= {
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    }
)


#openai.ChatCompletion.create(
#  model="gpt-3.5-turbo",
#  messages=[
#        {"role": "system", "content": "You are an AI model that helps people understand lots of information by summarizing points using clear, every day language."},
#        {"role": "user", "content": """{'data': {'Get': {'UnstructuredDocument': [{'filename': 'Recognising Aboriginal and Torrest Strait Islander peoples through a Voice - Information Booklet.pdf', 'tags': 'VoiceYes', 'text': 'The Voice will not have a program delivery function', 'upload_note': ''}, {'filename': 'Recognising Aboriginal and Torrest Strait Islander peoples through a Voice - Information Booklet.pdf', 'tags': 'VoiceYes', 'text': 'What is the Voice and what would it do? There has been a lot of work over many years to define what a Voice could look like. The following Voice design principles were agreed by the First Nations Referendum Working Group and were drawn from this work.', 'upload_note': ''}, {'filename': 'Recognising Aboriginal and Torrest Strait Islander peoples through a Voice - Information Booklet.pdf', 'tags': 'VoiceYes', 'text': 'The Voice will not have a veto power', 'upload_note': ''}]}}"""}
#    ]
#) 


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

selected_tag = st.empty()
st.session_state.selected_class = "UnstructuredDocument"

with selected_tag:
    st.session_state.selected_tag = st.selectbox('Select a Resource', ["VoiceYes", "VoiceNo"])

def reset_results():
    st.session_state['results'] = []
    st.session_state['results_table'] = pd.DataFrame(columns=['group_header', 'text_list'])

concepts_input, result_limit = st.columns(2)
# User input for concepts, comma separated
with concepts_input:
    st.session_state.concepts_input = st.text_input("search information on the Voice", "what will the Voice do?").split(", ")
with result_limit:
    st.session_state.result_limit = st.slider("result limit", 1, 10, 8)

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
            .get(st.session_state.selected_class, ["text", "filename", "upload_note", "tags"])  
            .with_near_text(nearText)  
            .with_limit(st.session_state.result_limit) 
            .with_where({
                "path": ["tags"],
                "operator": "Equal",
                "valueString": st.session_state.selected_tag
            })
            .do() 
        )
        print(response)
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
            grouped_df = df.groupby(['tags', 'upload_note','filename'])['text'].agg(aggregate_texts).reset_index()
            results_df = st.session_state.results_table
            
            for _, group in grouped_df.groupby(['tags', 'upload_note', 'filename']):
                # Create a markdown string for the group header
                group_header = f"`Article Name: ` {group['filename'].iloc[0]}    \n`Tags: ` {group['tags'].iloc[0]}  \n`Upload Note: ` {group['upload_note'].iloc[0]}"
                # Create a markdown string for the ordered list of texts
                text_list = "\n".join(f"{text}" for text in group['text'])
                # Append the group header and text list to the results DataFrame
                results_df = pd.concat([results_df, pd.DataFrame([{'group_header': group_header, 'text_list': text_list}])], ignore_index=True)
                 # Save the results DataFrame to the Streamlit session state
                st.session_state.results_table = results_df

for i in range(len(st.session_state.results_table)):
    st.markdown(st.session_state.results_table['group_header'][i])
    st.markdown(st.session_state.results_table['text_list'][i])
     
























