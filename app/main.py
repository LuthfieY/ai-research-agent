import streamlit as st
import os

st.set_page_config(page_title="Autonomous Research Agent", page_icon="🤖")

st.title("🤖 Autonomous Research Agent")

# Sidebar for debug info
with st.sidebar:
    st.header("System Status")
    if os.getenv("GEMINI_API_KEY"):
        st.success("GEMINI API Key Detected")
    else:
        st.error("Missing GEMINI API Key")
        
    if os.getenv("TAVILY_API_KEY"):
        st.success("Tavily API Key Detected")
    else:
        st.error("Missing Tavily API Key")

st.write("Welcome! Edit `app/main.py` and save to see this update instantly")

# Simple input to test interactivity
query = st.text_input("What should I research?")

if query:
    st.info(f"Prepare to research: {query}")
    # Later, we will hook this up to graph.py