import streamlit as st
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Weaviate
from langchain.chat_models import ChatOpenAI 
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain, RetrievalQAWithSourcesChain
from langchain.llms import HuggingFaceHub
from weaviate import Client, AuthApiKey
from langchain.chains.qa_with_sources.loading import load_qa_with_sources_chain
from weaviate.util import generate_uuid5
from datetime import date
from langchain.chains.question_answering import load_qa_chain

            
import langchain
langchain.verbose = False            

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

def add_to_weaviate(client, text_chunks, filename, url):
    embeddings = OpenAIEmbeddings()
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    
    # FAISS is a local vector store
    #vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    # add to weaviate with client input

    
    with client.batch(batch_size=10) as batch:
        for i, d in enumerate(text_chunks):  
          properties = {
              'text': d,
              'source': filename,
              'date': date.today().strftime("%Y-%m-%d"),
              'url': url 
          }
          
          batch.add_data_object(
              properties,
              'LangchainDocument',
              uuid=generate_uuid5(properties),
          )


def get_conversation_chain(vectorstore):
    chat_model_name = "gpt-4"
    llm = ChatOpenAI(model_name=chat_model_name)

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    #conversation_chain = ConversationalRetrievalChain.from_llm(
    #    llm=llm,
    #    retriever=vectorstore.as_retriever(),
    #    memory=memory
    #)
    conversation_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=docsearch.as_retriever(search_kwargs={"k": num_retrieved_documents})
    )

    return conversation_chain


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

  if "messages" not in st.session_state.keys(): # Initialize the chat message history
      st.session_state.messages = [
          {"role": "assistant", "content": "what would you like to know?"}
      ]

  vectorstore = Weaviate(client, index_name="LangchainDocument", text_key="text", attributes=["source", "url"])


  st.header("📚 your library 📚")

  st.write("do your own research about the referendum. here are some questions to get you started")
  #st.write("it uses information from across the political spectrum to provide answers to your questions about the upcoming referendum")

  # create 3 columns for the 3 questions
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
  
  st.write("otherwise ask your own question the chatbox below")

  if prompt := st.chat_input("e.g. what is the Voice, and what will it do?"): # Prompt for user input and save to chat history
      st.session_state.messages.append({"role": "user", "content": prompt})

  for message in st.session_state.messages: # Display the prior chat messages
      with st.chat_message(message["role"]):
          st.write(message["content"])

  # If last message is not from assistant, generate a new response
  if st.session_state.messages[-1]["role"] != "assistant":
      with st.chat_message("assistant"):
          with st.spinner("Thinking..."):
            memory = ConversationBufferMemory(
                memory_key='chat_history', return_messages=True)
            langchain.verbose = False
            chain = load_qa_with_sources_chain(
                ChatOpenAI(model_name="gpt-3.5-turbo",temperature=0), 
                chain_type="stuff"
                )                                                                                                                                                  
            docs = vectorstore.similarity_search(st.session_state.messages[-1]["content"], top_k=5)
            print(docs)
            response_dict = chain({"input_documents": docs, "question": st.session_state.messages[-1]["content"]}, return_only_outputs=True)                                                                                                                                                                     
            #output_text = response_dict['output_text']
            parts = response_dict['output_text'].split('SOURCES:')                                    
            #print(response_dict)                                                                                                    
            answer = parts[0].strip()
            #sources = parts[1].strip()
            unique_sources = list(set(doc.metadata['source'] for doc in docs))
            unique_sources_url = list(set(doc.metadata['url'] for doc in docs))

            # Create a list of formatted markdown links
            sources_links = [f"[{source}]({url})" for source, url in zip(unique_sources, unique_sources_url)]
            sources = '\n\n'.join(sources_links)

            # Replace commas with newline delimiters for the second part
            #sources = sources.replace(', ', '\n\n')

            answer += "\n\nSOURCES:\n\n" + sources

            # remove duplicaes from sources
            st.write(answer)
            # Add response to message history
            message = {"role": "assistant", "content": answer}
            st.session_state.messages.append(message) 
    

  with st.sidebar:
      st.subheader("Your documents")
      pdf_docs = st.file_uploader(
          "Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
      url = st.text_input("add the url this document came from")
      if st.button("Process"):
          with st.spinner("Processing"):
              # get pdf text
              raw_text = get_pdf_text(pdf_docs)

              # get the text chunks
              text_chunks = get_text_chunks(raw_text)

              # create vector store
              add_to_weaviate(client,text_chunks,pdf_docs[0].name, url)




if __name__ == '__main__':
  main()

