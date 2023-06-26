import streamlit as st
import pandas as pd
import helper

st.title("experimenting with partitioning pdfs")




from unstructured.partition.auto import partition_pdf

elements = partition_pdf("data/Australian Parliament Network effects.pdf")
pdf_data = pd.Series()



from unstructured.documents.elements import NarrativeText
from unstructured.partition.text_type import sentence_count




for element in elements[:100]:
    if isinstance(element, NarrativeText) and sentence_count(element.text) > 2:
        pdf_data = pd.concat([pdf_data, pd.Series(element.text)])


st.table(pdf_data)

st.header("current library contents")
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



