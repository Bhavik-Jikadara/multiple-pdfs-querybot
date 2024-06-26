import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.faiss import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from src.htmlTemplates import css, bot_template, user_template
import time


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

def get_vectorstore(text_chunks, api_key):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore, api_key):
    llm = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})

    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    load_dotenv()
    # Page config
    st.set_page_config(
        page_title="Multiple PDFs QueryBot",
        page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    # ---------------------------- ChatBot -------------------------------------------
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Multiple PDFs QueryBot :books:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    # ---------------------------- End of ChatBot -------------------------------------

    # ---------------------------- Sidebar section ------------------------------------
    with st.sidebar:
        st.title("About Project")
        st.write("**The Multiple PDFs QueryBot is a Python-based tool for interacting with multiple PDF documents through natural language queries.**\n* Users can ask questions about the content of the PDFs, and the app will deliver relevant answers based on the information within the documents.")
        st.subheader("Documents")
        api_key = st.text_input(label="Enter OpenAI api key", type="password", placeholder="OPENAI_API_KEY")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", accept_multiple_files=True)

        if st.button("Process"):
            with st.status("In process...", expanded=True, state="running") as status:
                # get pdf text
                st.write("Get the text from the PDFs files")
                raw_text = get_pdf_text(pdf_docs)
                time.sleep(5)

                # get the text chunks
                st.write("Dividing text into chunks")
                text_chunks = get_text_chunks(raw_text)
                time.sleep(3)

                # create vector store
                st.write("Passing chunks in vectorstore")
                vectorstore = get_vectorstore(text_chunks, api_key)
                time.sleep(1)
                status.update(
                    label="Successfully process! Now you can ask a question", state="complete", expanded=False)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore, api_key)

    # ---------------------------- Sidebar section ------------------------------------

if __name__ == '__main__':
    main()
