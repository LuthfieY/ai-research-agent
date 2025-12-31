import streamlit as st
import os
import pandas as pd
from app.graph import app_graph
from app.database import init_db, save_research, get_history

# Initialize DB on startup
init_db()

st.set_page_config(page_title="Lumina Research", page_icon="🔎", layout="wide")

# Centered Title & Subtitle with Reduced Gap & Custom CSS
st.markdown("""
<style>
div[data-testid="InputInstructions"] {
    display: none;
}
</style>

<div style='text-align: center; margin-bottom: 30px;'>
    <h1 style='margin-bottom: -15px;'>Lumina Research</h1>
    <p style='margin-top: 15px; opacity: 0.8;'>Enter a topic, and I'll research, write, and refine a report for you.</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR (Configuration & History) ---
with st.sidebar:
    with st.expander("🛠 Configuration", expanded=False):
        st.subheader("API Keys")
        user_gemini_key = st.text_input("Gemini API Key", type="password", help="Required for Research")
        user_tavily_key = st.text_input("Tavily API Key", type="password", help="Required for General Search")
        user_serpapi_key = st.text_input("SerpAPI Key", type="password", help="Required for Academic Journal Search")
        
        st.divider()
        st.subheader("Parameters")
        
        # Logic to filter Search Modes based on Keys
        mode_options = []
        if user_tavily_key or os.getenv("TAVILY_API_KEY"):
            mode_options.append("General")
        if user_serpapi_key or os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_API_KEY"):
            mode_options.append("Academic Journals")

        if not mode_options:
            search_mode = st.selectbox("Search Mode", ["No Search Keys Found"], disabled=True)
            st.error("Input Tavily/SerpAPI Key.")
        else:
            search_mode = st.selectbox("Search Mode", mode_options)
        
        citation_style = st.selectbox("Citation Style", ["IEEE", "APA", "BibTeX"])
        max_results = st.slider("Max Search Results", 1, 10, 3, help="Number of sources to fetch per query.")
        max_revisions = st.slider("Max Revisions", 1, 5, 2, help="Max number of critique & rewrite loops.")

    st.divider()
    
    if st.button("New Research", type="secondary", use_container_width=True):
        st.session_state["history_view"] = None
        st.session_state["final_state"] = None
        st.rerun()
    
    st.divider()
    
    history_data = get_history()
    if not history_data:
        st.info("No history yet.")
    else:
        for item in history_data:
            label = f"{item['timestamp'][:10]} - {item['topic'][:20]}..."
            if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                st.session_state["history_view"] = item
                st.rerun()

# --- MAIN CONTENT AREA ---

# Determine View Mode
view_item = st.session_state.get("history_view")

# If viewing history, show static report
if view_item:
    st.info(f"Viewing history: {view_item['timestamp']}")
    st.markdown(view_item['report'])
    
    st.divider()
    with st.expander("📚 References & Citations", expanded=True):
        # Display references from history
        refs = view_item.get('references', [])
        st.json(refs)
        
    if st.button("Back to Research"):
        st.session_state["history_view"] = None
        st.rerun()

# If NEW RESEARCH mode
else:
    # --- QUERY INPUT ---
    query = st.text_input("Research Topic:", placeholder="e.g. The future of solid state batteries")

    if st.button("Start Research") and query:
        # --- Input Validation ---
        if not (user_gemini_key or os.getenv("GEMINI_API_KEY")):
            st.error("❌ Gemini API Key is missing. Please enter it in the Settings above.")
            st.stop()
            
        if "No Search Keys Found" in search_mode:
            st.error("❌ No valid Search API Key (Tavily or SerpAPI) found. Please verify your keys.")
            st.stop()
        # ------------------------

        status_container = st.status("Initializing Agent...", expanded=True)
        
        current_state = {} 

        try:
            inputs = {"task": query}
            
            # Pass API keys & Configs via run config
            run_config = {"configurable": {
                "search_mode": search_mode,
                "citation_style": citation_style,
                "max_results": max_results,
                "max_revisions": max_revisions,
                "gemini_api_key": user_gemini_key,
                "tavily_api_key": user_tavily_key,
                "serpapi_api_key": user_serpapi_key
            }}
            
            # --- AGENT LOOP ---
            for output in app_graph.stream(inputs, config=run_config):
                for key, value in output.items():
                    if "content" in value and isinstance(value["content"], list):
                        current_content = current_state.get("content", [])
                        new_content = value["content"]
                        current_state["content"] = current_content + new_content
                        other_updates = {k: v for k, v in value.items() if k != "content"}
                        current_state.update(other_updates)
                    else:
                        current_state.update(value)

                    if key == "researcher":
                        new_content = value.get('content', [])
                        count = len(new_content)
                        status_container.markdown(f"**Researcher**: Found {count} new articles.")
                        with status_container.expander("📄 View Collected Sources", expanded=False):
                            for item in new_content:
                                st.write(f"- [{item.get('year', 'n.d')}] {item.get('title', 'Unknown')}")
                        status_container.update(label="🤔 Thinking... (Writer is composing)", state="running")
                        
                    elif key == "writer":
                        rev = value.get('revision_number')
                        draft_preview = value.get('draft', '')[:300] + "..."
                        status_container.markdown(f"**Writer**: Completed Draft Revision #{rev}")
                        with status_container.expander(f"📝 Preview Draft #{rev}", expanded=False):
                            st.write(draft_preview)
                        status_container.update(label="🕵️ Critic is reviewing...", state="running")
                        
                    elif key == "critique":
                        action = value.get('last_action')
                        critique_text = value.get('critique', '')
                        status_container.markdown(f"**Verdict:** {action}")
                        with status_container.expander("View Critique Feedback", expanded=True):
                            st.markdown("**Critique:**")
                            if action == "APPROVE":
                                st.success(critique_text)
                            else:
                                st.write(critique_text)
                        status_container.update(label=f"💡 Next Action: {action}", state="running")
                        
            status_container.update(label="Research Completed!", state="complete", expanded=False)
            st.session_state["final_state"] = current_state
            
            if current_state.get("draft"):
                save_research(query, current_state["draft"], current_state.get("content", []))
                st.toast("✅ Research saved to History!")
                
            st.toast("Research completed! Scroll down for References 📚") ## CHANGED MESSAGE

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()
            
    # --- RENDER FINAL OUTPUT (If available in session state) ---
    if "final_state" in st.session_state and st.session_state["final_state"]:
        final_state = st.session_state["final_state"]
        
        if final_state.get("draft"):
            st.divider()
            
            # CSS for Justified Text
            st.markdown("""
            <style>
            .stMarkdown p {
                text-align: justify;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(final_state["draft"])
            
            # --- REFERENCES SECTION (Bottom of Main Page) ---
            if final_state.get("content"):
                with st.expander("📚 References & Citations", expanded=False):
                    st.header("References")
                    
                    # 1. Table
                    ref_data = []
                    for i, item in enumerate(final_state["content"], 1):
                        ref_data.append({
                            "No": i,
                            "Year": item.get("year", "n.d."),
                            "Author": item.get("author", "Unknown"),
                            "Title": item.get("title", 'Unknown'),
                            "Source": item.get("source", "")
                        })
                    
                    st.dataframe(
                        ref_data, 
                        column_config={
                            "No": st.column_config.NumberColumn(width="small"),
                            "Year": st.column_config.TextColumn(width="small"),
                            "Author": "Author",
                            "Title": "Title",
                            "Source": st.column_config.LinkColumn("Link")
                        },
                        hide_index=True
                    )
                    
                    st.divider()
                    
                    # 2. Citation Generator
                    st.subheader("❝ Citation Generator")
                    
                    # Use current selectbox choice if available, else default
                    report_style = citation_style # This variable is available from the Config Expander above
                    citation_options = ["IEEE", "APA", "BibTeX"]
                    default_index = citation_options.index(report_style) if report_style in citation_options else 0
                    
                    citation_format = st.selectbox("Format", citation_options, index=default_index, key="cit_bottom_gen")
                    
                    citation_text = ""
                    for i, item in enumerate(final_state["content"], 1):
                        title = item.get("title", "Unknown Title")
                        year = item.get("year", "n.d.")
                        author = item.get("author", "Unknown Author")
                        url = item.get("source", "")
                        
                        if citation_format == "APA":
                            citation_text += f"{i}. {author}. ({year}). _{title}_. Retrieved from {url}\n\n"
                        elif citation_format == "IEEE":
                            citation_text += f"[{i}]. {author}, \"{title},\" {year}. [Online]. Available: {url}.\n\n"
                        elif citation_format == "BibTeX":
                            clean_author = author.split()[0].lower() if author else "unknown"
                            cit_key = f"{clean_author}{year}{i}"
                            citation_text += f"""@misc{{{cit_key},
        author = {{{author}}},
        title = {{{title}}},
        year = {{{year}}},
        howpublished = {{\\url{{{url}}}}}
}}\n\n"""

                    st.code(citation_text, language="text" if citation_format != "BibTeX" else "latex")
