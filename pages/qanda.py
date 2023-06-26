import streamlit as st
#from langchain.llms import OpenAI
#from langchain import PromptTemplate



code = """
template =
What follows is:
- a question,
- a set of relevant context snippets for that question.

Please answer the question using only the context provided. If the context does not exist, or does not answer the question, please respond with "No context available"

QUESTION: {question}
CONTEXT: {context}

YOUR RESPONSE: 
"

prompt = PromptTemplate(
    input_variables=["question","context"],
    template=template
)

def load_LLM():
    llm = OpenAI(temperature=0)
    return llm

llm = load_LLM()

"""

# Streamlit UI
st.set_page_config(page_title="Q&A", page_icon=":shark:")
st.markdown(code)