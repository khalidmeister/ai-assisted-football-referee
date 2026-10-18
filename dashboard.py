import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Page Config
st.set_page_config(page_title="AI Football Referee", page_icon="⚽", layout="wide")
st.title("⚽ AI Football Referee Assistant (IFAB Laws of the Game)")
st.caption("Powered by ChromaDB Vector Search + Gemini 1.5 Flash (Google AI Studio)")
st.markdown("""
Sample Questions that you can choose from:
- What is yellow card called?
- What happen if i throw shirt for celebration and my goal disallowed?
- Why the foul is visible but the game still on?
""")

# 🔑 Sidebar untuk Input API Key Gemini Gratisan
st.sidebar.title("🔑 Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key (Free):", type="password")

# Fallback otomatis jika ada di st.secrets atau environment variable
if not api_key:
    api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

# 1. Load Vector DB (Cached agar cepat)
@st.cache_resource
def load_rag():
    embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vector_db = Chroma(
        collection_name="ifab_law_12_prod_grade",
        embedding_function=embedding_model,
        persist_directory="./chroma_db"
    )
    return vector_db

vector_db = load_rag()

# 2. UI Chat Input
user_query = st.text_input("Ask any football rule question (e.g., Mohamed Salah shirt removal rule):")

if user_query:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar to run the LLM Synthesis.")
        st.stop()
        
    with st.spinner("Searching IFAB Rulebook & Generating Verdict with Gemini..."):
        # Inisialisasi Gemini 1.5 Flash
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=api_key,
            temperature=0
        )
        
        # Retrieval
        results = vector_db.similarity_search_with_relevance_scores(user_query, k=2)

        print(results)
        
        if not results:
            st.warning("No relevant document found.")
        else:
            top_doc, top_score = results[0]
            
            # Prompt + Chain
            prompt = ChatPromptTemplate.from_template("""
            You are an official FIFA Referee Assistant. Answer using ONLY the IFAB context below.
            Simplify the complex legal language into plain, easy-to-understand English.
            Cite the Law and Page number if available.
            
            Context: {context}
            Question: {question}
            Answer:
            """)
            
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({"context": top_doc.page_content, "question": user_query})
            
            # Display Result
            st.success("Verdict Generated!")
            st.markdown(f"### 🤖 Referee Decision:\n{answer}")
            
            # Display Source Citation
            with st.expander(f"📖 Retrieved Context (Relevance Score: {top_score:.4f})"):
                st.write(top_doc.page_content)
                # st.json(top_doc.metadata)