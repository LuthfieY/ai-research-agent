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
    search_mode = st.selectbox("Search Mode", ["General", "Academic Journals"])

query = st.text_input("Research Topic:", placeholder="e.g. The future of solid state batteries")

if st.button("Start Research") and query:
    status_container = st.status("Initializing Agent...", expanded=True)
    
    current_state = {} 

    try:
        inputs = {"task": query, "search_mode": search_mode}
        
        for output in app_graph.stream(inputs):
            for key, value in output.items():
                current_state.update(value)

                if key == "researcher":
                    new_content = value.get('content', [])
                    count = len(new_content)
                    
                    status_container.markdown(f"✅ **Researcher**: Found {count} new articles.")
                    # Show titles of found articles
                    with status_container.expander("📄 View Collected Sources", expanded=False):
                        for item in new_content:
                            st.write(f"- [{item.get('year', 'n.d')}] {item.get('title', 'Unknown')}")
                            
                    status_container.update(label="🤔 Thinking... (Writer is composing)", state="running")
                    
                elif key == "writer":
                    rev = value.get('revision_number')
                    draft_preview = value.get('draft', '')[:300] + "..."
                    
                    status_container.markdown(f"✍️ **Writer**: Completed Draft Revision #{rev}")
                    # Show draft snippet
                    with status_container.expander(f"📝 Preview Draft #{rev}", expanded=False):
                        st.write(draft_preview)
                        
                    status_container.update(label="🕵️ Critic is reviewing...", state="running")
                    
                elif key == "critique":
                    action = value.get('last_action')
                    critique_text = value.get('critique', '')
                    
                    status_container.markdown(f"**Verdict:** {action}")
                    with status_container.expander("🔍 View Critique Feedback", expanded=True):
                        st.markdown("**Critique:**")
                        if action == "APPROVE":
                            st.success(critique_text)
                        else:
                            st.write(critique_text)
                            
                    status_container.update(label=f"💡 Next Action: {action}", state="running")
                    
        status_container.update(label="Research Completed!", state="complete", expanded=False)
        st.session_state["final_state"] = current_state
        st.toast("Research completed! Check the Sidebar for References 📚")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.stop()
        
if "final_state" in st.session_state:
    final_state = st.session_state["final_state"]
    
    if final_state and final_state.get("draft"):
        # 1. Main Content: Final Report (Full Width)
        st.divider()
        st.header("📄 Final Report")
        
        # Inject CSS for justified text
        st.markdown("""
        <style>
        .stMarkdown p {
            text-align: justify;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(final_state["draft"])
        
        if final_state.get("content"):
            with st.sidebar:
                st.divider()
                st.header("📚 References")
                
                # Format data for table
                ref_data = []
                for i, item in enumerate(final_state["content"], 1):
                    ref_data.append({
                        "No": i,
                        "Year": item.get("year", "n.d."),
                        "Author": item.get("author", "Unknown"),
                        "Title": item.get("title", 'Unknown'),
                        "Source": item.get("source", "")
                    })
                
                # Display Compact Table
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
                
                # Citation Generator
                st.subheader("❝ Citation Generator")
                citation_format = st.selectbox("Format", ["APA", "IEEE", "BibTeX"])
                
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
                        # Create a simple citation key from author + year + index
                        clean_author = author.split()[0].lower() if author else "unknown"
                        cit_key = f"{clean_author}{year}{i}"
                        citation_text += f"""@misc{{{cit_key},
                                        author = {{{author}}},
                                        title = {{{title}}},
                                        year = {{{year}}},
                                        howpublished = {{\\url{{{url}}}}}
                                    }}\n\n"""

                st.markdown(citation_text)
