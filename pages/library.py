import streamlit as st
import pandas as pd
import src.helper



st.header("current library contents")
show_library = False
# API_KEY = os.environ(..)

# url to embed into personal library
# https://towardsdatascience.com/a-multi-page-interactive-dashboard-with-streamlit-and-plotly-c3182443871a

st.button(
    label="fetch from library",
    on_click=src.helper.fetch_from_weaviate(
        src.helper.format_graphql_query("test")))

# unsure here of how i get the response into a table

st.table(pd.read_csv("data/parsed_pdf.csv"))
graphql_response = ""

st.button(
    label="generate summaries",
    on_click=src.helper.summarise_embeds(graphql_response) # changes graphql_response
)

formatted_graphql_response = src.helper.format_for_viewing(graphql_response)
# st.table(graphql_response)



