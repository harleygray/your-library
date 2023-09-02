import streamlit as st
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Weaviate
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from langchain.llms import HuggingFaceHub
from weaviate import Client, AuthApiKey
from weaviate.util import generate_uuid5
from datetime import date
from langchain.chains.question_answering import load_qa_chain

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def add_to_weaviate(client, text_chunks, filename, user_tags):
    embeddings = OpenAIEmbeddings()
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    
    # FAISS is a local vector store
    #vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    # add to weaviate with client input

    
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(text_chunks):  
          st.write(d)
          properties = {
              'text': d,
              'filename': filename,
              'date': date.today().strftime("%Y-%m-%d"),
              'tags': user_tags 
          }
          batch.add_data_object(
              properties,
              'LangchainDocument',
              uuid=generate_uuid5(properties),
          )


#def load_weaviate(client):
#    
#    return vectorstore


def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

#def handle_userinput(user_question):
#    response = st.session_state.messages({'question': user_question})
#    st.session_state.chat_history = response['chat_history']
#
#    for i, message in enumerate(st.session_state.chat_history):
#        if i % 2 == 0:
#            st.write(user_template.replace(
#                "{{MSG}}", message.content), unsafe_allow_html=True)
#        else:
#            st.write(bot_template.replace(
#                "{{MSG}}", message.content), unsafe_allow_html=True)

def main():
  load_dotenv()

  WEAVIATE_URL = os.getenv("WEAVIATE_URL")
  WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
  OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")




  client = Client(
      url=WEAVIATE_URL,
      auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY),
      additional_headers= {
          "X-OpenAI-Api-Key": OPENAI_API_KEY,
      }
  )

  st.set_page_config(
      page_icon='📚', 
      page_title="your library",
      initial_sidebar_state="collapsed")
  st.write(css, unsafe_allow_html=True)

  if "messages" not in st.session_state.keys(): # Initialize the chat message history
      st.session_state.messages = [
          {"role": "assistant", "content": "ask a question about the Voice to Parliament"}
      ]

  vectorstore = Weaviate(client, index_name="LangchainDocument", text_key="text")

  if "conversation" not in st.session_state:
      st.session_state.conversation = None
#  if "chat_history" not in st.session_state:
#      st.session_state.chat_history = None

  #st.session_state.conversation = get_conversation_chain(
  #      load_weaviate(client))
  st.header("📚 your library 📚")

  st.write("your library is a tool to help you do your own research")
  st.write("it uses information from across the political spectrum to provide answers to your questions about the upcoming referendum")

  if prompt := st.chat_input("Your question"): # Prompt for user input and save to chat history
      st.session_state.messages.append({"role": "user", "content": prompt})

  for message in st.session_state.messages: # Display the prior chat messages
      with st.chat_message(message["role"]):
          st.write(message["content"])

  # If last message is not from assistant, generate a new response
  if st.session_state.messages[-1]["role"] != "assistant":
      with st.chat_message("assistant"):
          with st.spinner("Thinking..."):
            docs = vectorstore.similarity_search(prompt, top_k=10)
            
            chain = load_qa_chain(
              ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0))
            #response = st.session_state.conversation({'question': prompt})
            assistant_response = chain.run(input_documents=docs, question=prompt)
            st.write(assistant_response)
            message = {"role": "assistant", "content": assistant_response}
            st.session_state.messages.append(message) # Add response to message history
    

  with st.sidebar:
      st.subheader("Your documents")
      pdf_docs = st.file_uploader(
          "Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
      tags = st.text_input("tag this document with keywords")
      if st.button("Process"):
          with st.spinner("Processing"):
              # get pdf text
              raw_text = get_pdf_text(pdf_docs)

              # get the text chunks
              text_chunks = get_text_chunks(raw_text)

              # create vector store
              add_to_weaviate(client,text_chunks,pdf_docs[0].name, tags)

              



if __name__ == '__main__':
  main()


#  iframe = """
#  <iframe
#    src="https://your-library.streamlit.app/library_search/?embed=true"
#    height="450"
#    style="width:100%;border:none;"
#  ></iframe>
#  """
#
#  components.html(iframe, height=450)


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