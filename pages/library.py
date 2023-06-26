import streamlit as st
import pandas as pd
import helper


st.title("current library contents")



show_library = False
# API_KEY = os.environ(..)



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

formatted_graphql_response = helper.format_for_viewing(graphql_response)
# st.table(graphql_response)



