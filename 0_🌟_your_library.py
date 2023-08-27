from urllib import parse
import streamlit as st
import streamlit.components.v1 as components

from dotenv import load_dotenv
import os
import pandas as pd
import json
from datetime import date

st.set_page_config(
    page_icon='📚', 
    page_title="your library",
    initial_sidebar_state="collapsed")

st.header("📚 your library 📚")

st.write("your library is a tool to help you understand the world")
st.write("this website is a work in progress.  here's the functionality available now")


# link to library_search.py
st.header("search your library")   
st.markdown("this page allows you to search information relevant to the Yes campaign for the Voice to Parliament referendum")

iframe = """
<iframe
  src="https://your-library.streamlit.app/library_search/?embed=true"
  height="450"
  style="width:100%;border:none;"
></iframe>
"""

components.html(iframe, height=450)


## link to unstructured_document_upload.py
#st.header("upload a document")   
#st.markdown("this page allows you to upload any document (works best for text or pdf). any text in the document is organised, cleaned, then added to a [vector database](https://weaviate.io/). this allows you to query the information in that text - a personal search engine.")
#
#iframe = """
#<iframe
#  src="https://your-library.streamlit.app/document_upload/?embed=true"
#  height="450"
#  style="width:100%;border:none;"
#></iframe>
#"""
#
#components.html(iframe, height=450)
#
#
#
#
#
## link to abc_article.py
#st.header("add abc news article")   
#st.markdown("""
#    here you can link to an australian broadcasting corporation (abc) article and have it added to your library. the abc is a state-funded news organisation and an impactful source of information. 
#
#    this page will eventually be an automated pipeline; article uploaded > added to your library. for now, you can add an article by pasting the url into the text box below.
#    """
#)
#
#
#iframe = """
#<iframe
#  src="https://your-library.streamlit.app/abc_article/?embed=true"
#  height="450"
#  style="width:100%;border:none;"
#></iframe>
#"""
#
#components.html(iframe, height=450)
#