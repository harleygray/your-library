import os
import streamlit as st
from dotenv import load_dotenv
from weaviate.util import generate_uuid5
from weaviate import Client, AuthApiKey
import pandas as pd
from apify_client import ApifyClient
import json
import requests

def apify_run(apify_client, url, only_new_articles=True):
    run_input = {
        "startUrls": [{ "url": url }],
        "onlyNewArticles": False,
        "onlyNewArticlesPerDomain": only_new_articles,
        "onlyInsideArticles": True,
        "enqueueFromArticles": False,
        "crawlWholeSubdomain": False,
        "onlySubdomainArticles": False,
        "scanSitemaps": False,
        "saveSnapshots": False,
        "useGoogleBotHeaders": False,
        "minWords": 50,
        "mustHaveDate": True,
        "isUrlArticleDefinition": {
            "minDashes": 4,
            "hasDate": True,
            "linkIncludes": [
                "article",
                "storyid",
                "?p=",
                "id=",
                "/fpss/track",
                ".html",
                "/content/",
            ],
        },
        "proxyConfiguration": { "useApifyProxy": True },
        "useBrowser": False,
        "extendOutputFunction": """($) => {
        const result = {};
        // Uncomment to add a title to the output
        // result.pageTitle = $('title').text().trim();

        return result;
        }""",
    }
    run = apify_client.actor("lukaskrivka/article-extractor-smart").call(run_input=run_input)
    return run

def classification_query(HUGGINGFACE_API_KEY, payload):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
    data = json.dumps(payload)
    response = requests.request("POST", API_URL, headers=headers, data=data)
    return json.loads(response.content.decode("utf-8"))

def main():
    # Load environment variables
    load_dotenv()
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    APIFY_API_KEY = os.getenv("APIFY_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

    # Todo: change from Weaviate-handled embeddings to a pipeline, logging using Comet
    weaviate_client = Client(
      url=WEAVIATE_URL,
      auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY),
      additional_headers= {
          "X-OpenAI-Api-Key": OPENAI_API_KEY,
      }
    )

    # Initialize the ApifyClient with your API token
    apify_client = ApifyClient(APIFY_API_KEY)

    # Streamlit UI setup
    st.set_page_config(page_icon='📥', page_title="your library", initial_sidebar_state="collapsed")
    st.header("📥 input pipeline 📥")
    st.write("control panel to add and modify items in library")

    # Set initial state
    keys = ['scraped_formatted_data']
    default_values = [
        None
    ]

    for key, default_value in zip(keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default_value




    
    url = st.text_input("choose a url to scrape data from")
    only_new_articles = st.checkbox("only new articles?", value=True)
    if st.button("process"):
        with st.spinner("processing"):
            # APIFY call to get scraped data
            scraped_data = apify_run(apify_client, url, only_new_articles)
            scraped_formatted_data = pd.DataFrame(columns=['url', 'title', 'date', 'author', 'publisher', 'keywords', 'tags', 'text'])
            #st.write("outpupt:")
            #st.write(scraped_data)
            # Fetch and print Actor results from the run's dataset (if there are any)
            for item in apify_client.dataset(scraped_data["defaultDatasetId"]).iterate_items():
                scraped_formatted_data = pd.concat([
                    pd.DataFrame([[
                        item['url'], item['title'], item['date'], item['author'], item['publisher'], item['keywords'], item['tags'], item['text']
                    ]], columns=scraped_formatted_data.columns),
                    scraped_formatted_data], ignore_index=True)

            # Filter out any audio uploads
            #scraped_formatted_data = scraped_formatted_data.loc[~scraped_formatted_data['url'].str.startswith('https://www.abc.net.au/listen/')].reset_index(drop=True)
            

        
            # Remove duplicates

            # Classify as pro-voice / anti-voice
            # Todo: allow refresh for missed classifications
            #with st.spinner("classification"):
            #    for idx, row in scraped_formatted_data.iterrows():
            #        st.write(row['url'])
            #        # classification
            #        
            #        st.write(classification_query(HUGGINGFACE_API_KEY, {
            #            "inputs": row['text'],
            #            "parameters": {"candidate_labels": ['pro-voice', 'anti-voice']}}))



            # Summary of chunk

            # Future: named entity recognition

            # Store in variable - pass to manual review/editing phase
            st.session_state.scraped_formatted_data = pd.DataFrame(scraped_data)

    st.write(st.session_state.scraped_formatted_data)
    table_widget = st.empty()
    # Display table when there's data
    if st.session_state.scraped_formatted_data is None:
        table_widget.empty() # If there's no data, clear the placeholder
    else:
        table_widget.data_editor(
            st.session_state.scraped_formatted_data, 
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
                # Update the corresponding row in 'scraped_formatted_data' with the changes
                for column, new_value in changes.items():
                    st.session_state.scraped_formatted_data.loc[row_index,column] = new_value

            # Create a mask that identifies which rows are NOT marked for removal
            mask = st.session_state.scraped_formatted_data['to remove'] == False

            # Filter the rows in scraped_formatted_data using the mask
            filtered_scraped_formatted_data = st.session_state.scraped_formatted_data[mask]

            # Initialize an empty list to store the data objects
            data_objects = []

            # Iterate through the rows of the filtered DataFrame
            for _, row in filtered_scraped_formatted_data.iterrows():
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
            st.session_state.scraped_formatted_data = data_objects




if __name__ == '__main__':
  main()

