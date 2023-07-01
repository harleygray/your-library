from urllib import parse
import streamlit as st
import helper
import pandas as pd
import numpy as np



from unstructured.partition.auto import partition
from unstructured.documents.elements import *
from unstructured.partition.text_type import sentence_count



st.title("your library")
st.markdown("upload any document to store its meaning")
# need to install pip package to use this 
st.write(helper.format_for_viewing())

## Upload any document
raw_document = st.file_uploader("upload")
if raw_document is not None:
    st.write("Success: ", raw_document.name," uploaded!")
    doc_elements = partition(file=raw_document)
    doc_data = pd.DataFrame(columns=
                            ["Text",
                             "FigureCaption", 
                             "NarrativeText", 
                             "ListItem", 
                             "Title", 
                             "Address", 
                             "Table", 
                             "PageBreak", 
                             "Header", 
                             "Footer"])

    for element in doc_elements:
        element_type = type(element).__name__
        if element_type in doc_data.columns:
            new_row = pd.DataFrame({element_type: [element.text]})
            doc_data[element_type] = pd.concat([doc_data[element_type], new_row], ignore_index=True)
    # Create a DataFrame for each type of element
    #df = pd.DataFrame()
    """     for element in doc_elements:
        element_type = type(element).__name__
        doc_data[element_type] = pd.concat(doc_data[element_type],pd.Series([element.text]), ignore_index=True) """

    
    # For now, only put NarrativeText in
#    for element in doc_elements:
#        element_type = str(type(element).__name__)
#        if element_type == 'NarrativeText':
#            new_row = pd.DataFrame({element_type: [element.text]})
#            #doc_data[element_type] = pd.concat([doc_data[element_type], new_row], ignore_index=True)
#            new_row
#            doc_data
#
#            #doc_data = doc_data.fillna(method='ffill')
#            element_type
#            element.text
        
    """     for element in doc_elements:
        # This is where it makes sense to have classes of document types. 
        # Option for user to select what element types are allowed. They are parameters for the underlying document type (types/classes)
        # Maybe they don't actually need to be distinct types. maybe storing the metadata about e.g. how many of each of the Element objects:
        # 
        #if isinstance(element, NarrativeText) and sentence_count(element.text) > 2:
        #doc_data = pd.concat([doc_data, pd.Series([format("{0}: \n{1}", element.id, element.text)])])
        doc_data = pd.concat([doc_data, pd.Series("{0}: \n{1}".format(element.id, element.text))])


    """

    st.table(doc_data['NarrativeText'])

    parsed_pdf = pd.read_csv("./data/parsed_pdf.csv")
    # show to user the processed pdf. get confirmation before adding to weaviate
    st.table(parsed_pdf)
    st.button(label="upload to database",on_click=helper.send_to_weaviate(parsed_pdf))
    





# show all items in database
## display a new page














# raw_pdf is now a variable


# set a goal, mindfully
st.header("Current goal")
st.text("Assemble the fullstack skeleton")

# add new note
user_input = st.text_input("add new note")
if user_input is not None:
    st.write('User input: ', user_input)




# import current file noting metadata.
current_list = pd.read_csv("./data/notes.csv")

# function to append new entry to .csv file






# CSS to inject contained in a string
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_table_row_index, unsafe_allow_html=True)

# display contents of .csv file
st.table(current_list)



# use Unstructured to extract meaning and prepare for embedding


# embed in weaviate using the module. 

