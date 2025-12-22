import streamlit as st
import os
from app.graph import app_graph

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

st.markdown("Enter a topic, and I'll research, write, and refine a report for you.")

with st.sidebar:
    st.header("Settings")
    st.info("Using Gemini 2.5 Flash + Tavily Search")

query = st.text_input("Research Topic:", placeholder="e.g. The future of solid state batteries")

if st.button("Start Research") and query:
    status_container = st.status("Initializing Agent...", expanded=True)
    
    final_state = {} 

    try:
        inputs = {"task": query}
        
        for output in app_graph.stream(inputs):
            for key, value in output.items():
                final_state.update(value)

                if key == "researcher":
                    status_container.write(f"🔍 **Researcher**: Gathered {len(value.get('content', []))} new sources.")
                elif key == "writer":
                    rev = value.get('revision_number')
                    status_container.write(f"✍️ **Writer**: Drafted revision #{rev}.")
                elif key == "critique":
                    action = value.get('last_action')
                    status_container.write(f"🕵️ **Critic**: Feedback - {action}")
                    
        status_container.update(label="Research Completed!", state="complete", expanded=False)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.stop()
        
    if final_state and final_state.get("draft"):
        st.divider()
        st.header("📄 Final Report")
        st.markdown(final_state["draft"])
        
        st.divider()
        st.header("📚 Sources Used")
        if final_state.get("content"):
            for i, item in enumerate(final_state["content"], 1):
                st.markdown(f"**[{i}] {item.get('source')}**")
                with st.expander(f"Snippet from source {i}"):
                    st.caption(item.get('content')[:500] + "...")
    else:
        st.warning("No report was generated.")