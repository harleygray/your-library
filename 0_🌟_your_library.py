import os
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from datetime import date
from weaviate import Client, AuthApiKey
from weaviate.util import generate_uuid5
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI 
from langchain.prompts import ChatPromptTemplate
from langchain.chains.qa_with_sources.loading import load_qa_with_sources_chain
from langchain.vectorstores import Weaviate
import comet_llm
import json
from collections import defaultdict

# Initialize Langchain settings
import langchain
langchain.verbose = False
    
# Extract text from PDF files
def get_pdf_text(pdf_docs):
    return "".join(page.extract_text() for pdf in pdf_docs for page in PdfReader(pdf).pages)


# Split text into manageable chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_text(text)


# Add text chunks to Weaviate
def add_to_weaviate(client, text_chunks, filename, url):
    embeddings = OpenAIEmbeddings()
    with client.batch(batch_size=10) as batch:
        for chunk in text_chunks:
            properties = {
                'text': chunk, 
                'source': filename, 
                'date': date.today().strftime("%Y-%m-%d"), 
                'url': url}
            batch.add_data_object(properties, 'LangchainDocument', uuid=generate_uuid5(properties))



def main():
    # Load environment variables
    load_dotenv()
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    COMET_API_KEY = os.getenv("COMET_API_KEY")
    COMET_WORKSPACE = os.getenv("COMET_WORKSPACE")
    COMET_PROJECT_NAME = os.getenv("COMET_PROJECT_NAME")


    comet_llm.init(
        api_key = COMET_API_KEY,
        workspace = COMET_WORKSPACE,
        project = COMET_PROJECT_NAME
    ) 

    # Todo: change from Weaviate-handled embeddings to a pipeline, logging using Comet
    client = Client(
      url=WEAVIATE_URL,
      auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY),
      additional_headers= {
          "X-OpenAI-Api-Key": OPENAI_API_KEY,
      }
    )

    # Streamlit UI setup
    st.set_page_config(page_icon='📚', page_title="your library", initial_sidebar_state="collapsed")
    st.header("📚 your library 📚")
    st.write("click one of the options below to start researching")

    # Question buttons
    button1, button2, button3 = st.columns(3)
    with button1:
        if st.button("what is the Voice, and what will it do?"):
            st.session_state.messages.append({"role": "user", "content": "what is the Voice, and what will it do?"})
    with button2:
        if st.button("what is the case for a Yes vote?"):
            st.session_state.messages.append({"role": "user", "content": "what is the case for a Yes vote?"})
    with button3:
        if st.button("what is the case for a No vote?"):
            st.session_state.messages.append({"role": "user", "content": "what is the case for a No vote?"})

    st.write("you can also type a question in the text box at the bottom of the page")


    # Chatbox initialisation
    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {"role": "assistant", "content": "what would you like to know?"}
        ]
    vectorstore = Weaviate(client, index_name="LangchainDocument", text_key="text", attributes=["source", "url"])

    # User input
    if prompt := st.chat_input("e.g. what is the Voice, and what will it do?"): 
        st.session_state.messages.append({"role": "user", "content": prompt})
     # Display prior chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If last message is not from assistant, generate a new response
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Retrieve documents to use in context
                docs = vectorstore.similarity_search(st.session_state.messages[-1]["content"], top_k=5)

                # Format docs for input to LLM
                # Initialize a defaultdict to hold grouped documents
                grouped_documents = defaultdict(list)

                # Iterate through the list and group by metadata
                for doc in docs:
                    metadata_key = json.dumps(doc.metadata, sort_keys=True)  # Convert the metadata dictionary to a sorted JSON string
                    grouped_documents[metadata_key].append(doc)

                # Initialize an empty string to store the formatted context
                formatted_context = ""
                sources_links = ""
                # Iterate through the grouped documents to format them
                for idx, (metadata, docs) in enumerate(grouped_documents.items(), 1):
                    formatted_context += f"\nSource {idx}: {json.loads(metadata)['source']}\n"
                    sources_links += f"\nSource {idx}: [{json.loads(metadata)['source']}]({json.loads(metadata)['url']})\n"
                    for doc_idx, doc in enumerate(docs, 1):
                        formatted_context += f"\nDocument {doc_idx}: {doc.page_content}\n"

                # Format message for input to LLM
                prompt_template = "Use the following context block to answer a user question: `{context}`\nThe best answer will use context most relevant to the user question and respond in clear sentences that are easy to read (sometimes using dotpoints). Once you answer the question, briefly discuss the context wholistically."
                template = ChatPromptTemplate.from_messages([
                    ("system", prompt_template),
                    ("user", "{user_input}")
                ])
                
                formatted_message = template.format_messages(
                    context=formatted_context,
                    user_input=st.session_state.messages[-1]["content"]
                )

                # Get response from LLM
                llm = ChatOpenAI(model_name="gpt-3.5-turbo",temperature=0)
                response = llm(formatted_message)

                # Final format of response with sources
                answer = response.content + "\n\n" + sources_links
                
    
                # Log the interaction
                comet_llm.log_prompt(
                    prompt=st.session_state.messages[-1]["content"],
                    prompt_template=prompt_template,
                    prompt_template_variables=formatted_context,
                    output=answer,
                )

                # Add response to message history
                st.write(answer)
                message = {"role": "assistant", "content": answer}
                st.session_state.messages.append(message) 
                


    with st.sidebar:
        st.subheader("upload documents")
        pdf_docs = st.file_uploader("upload a .pdf  and click on 'Process'", accept_multiple_files=False)
        url = st.text_input("add the url this document came from")
        if st.button("Process"):
            with st.spinner("Processing"):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                # To do: calculate embeddings, log to Comet
                add_to_weaviate(client,text_chunks,pdf_docs[0].name, url)


if __name__ == '__main__':
  main()

