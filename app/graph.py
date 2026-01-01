import os
import json
from typing import List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults 

from app.agent_types import AgentState
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

def get_llm(config):
    configurable = config.get("configurable", {})
    api_key = configurable.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("WARNING: Gemini API Key missing.")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=api_key
    )

def researcher_node(state: AgentState, config):
    """
    Research Agent: Generates search queries based on task/critique and executes them.
    Supports "Academic Journals" mode via SerpAPI (Google Scholar).
    """
    print("--- Researcher Node Running ---")
    
    try:
        llm = get_llm(config)
    except Exception as e:
        print(f"LLM Init Error: {e}")
        return {"content": []}

    task = state["task"]
    critique = state.get("critique")
    
    configurable = config.get("configurable", {})
    search_mode = configurable.get("search_mode", "General")
    
    if critique:
        prompt = f"""
        You are a researcher. 
        User Task: {task}
        Critique on previous draft: {critique}
        
        Generate 2 specific search queries to gather missing information addressed in the critique.
        Return ONLY a JSON list of strings, e.g., ["query1", "query2"].
        """
    elif search_mode == "Academic Journals":
        prompt = f"""
        You are an academic researcher. 
        User Task: {task}
        
        Generate 3 advanced search queries to find ACADEMIC SOURCES (Journals, Research Papers, Theses). 
        Include terms like "journal", "study", "analysis", "PDF", "doi", or specific database names if relevant.
        Focus on finding credible, peer-reviewed information.
        
        Return ONLY a JSON list of strings, e.g., ["query1", "query2", "query3"].
        """
    else:
        prompt = f"""
        You are a researcher. 
        User Task: {task}
        
        Generate 3 broad search queries to start researching this topic.
        Return ONLY a JSON list of strings, e.g., ["query1", "query2", "query3"].
        """
        
    try:
        response = llm.invoke(prompt)
        content = response.content.replace("```json", "").replace("```", "").strip()
        queries = json.loads(content)
    except Exception as e:
        print(f"JSON Parsing failed or LLM error: {e}. Fallback to original task.")
        queries = [task]

    print(f"Searching for: {queries}")
    
    clean_results: List[ResearchResult] = []
    
    configurable = config.get("configurable", {})
    serp_key = configurable.get("serpapi_api_key") or os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_API_KEY")
    tavily_key = configurable.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
    max_results = configurable.get("max_results", 3)

    for q in queries:
        # --- Academic Search Logic (SerpAPI) ---
        if search_mode == "Academic Journals" and serp_key and GoogleSearch:
            print(f"DEBUG: Using SerpAPI (Google Scholar) for {q}")
            try:
                params = {
                    "engine": "google_scholar",
                    "q": q,
                    "api_key": serp_key,
                    "num": max_results
                }
                search = GoogleSearch(params)
                results = search.get_dict().get("organic_results", [])
                
                for r in results:
                    pub_info = r.get("publication_info", {})
                    summary = pub_info.get("summary", "")
                    
                    import re
                    year_match = re.search(r'\b(19|20)\d{2}\b', summary)
                    year = year_match.group(0) if year_match else "n.d."
                    
                    author = summary.split("-")[0].strip() if "-" in summary else "Unknown Author"

                    clean_results.append({
                        "title": r.get("title", "Unknown Title"),
                        "year": year,
                        "author": author,
                        "source": r.get("link", ""),
                        "content": r.get("snippet", "")
                    })
            except Exception as e:
                print(f"SerpAPI Error: {e}. Falling back to Tavily.")
                pass

        # --- General Search Logic (Tavily) ---
        else:
            if search_mode == "Academic Journals" and not serp_key:
                print("WARNING: Academic Mode selected but SERP_API_KEY missing. Falling back to Tavily.")

            try:
                tavily_tool = TavilySearchResults(max_results=max_results, tavily_api_key=tavily_key)
                
                search_results = tavily_tool.invoke(q)
                if search_results and isinstance(search_results, list):
                    for result in search_results:
                        pub_date = result.get('published_date', '')
                        year = pub_date[:4] if pub_date else 'n.d.'
                        
                        clean_results.append({
                            "title": result.get('title', 'Unknown Title'),
                            "year": year,
                            "author": result.get('author', 'Unknown'),
                            "source": result.get('url', 'Unknown Source'),
                            "content": result.get('content', '')
                        })
            except Exception as e:
                print(f"Tavily Error for {q}: {e}")
            
    print(f"DEBUG: Researcher found {len(clean_results)} results")
    return {"content": clean_results}

def writer_node(state: AgentState, config):
    """
    Writer Agent: Formats the structured data into a prompt.
    """
    print("--- Writer Node Running ---")
    
    llm = get_llm(config)
    
    context_string = ""
    if not state.get("content"):
        return {
            "draft": "Sorry, I could not find any relevant information to write a report.",
            "revision_number": state.get("revision_number", 0) + 1
        }

    for i, result in enumerate(state["content"], 1):
        context_string += f"[{i}] Title: {result['title']}\nAuthor: {result.get('author', 'Unknown')}\nYear: {result['year']}\nSource: {result['source']}\nContent: {result['content']}\n\n"
    
    configurable = config.get("configurable", {})
    citation_style = configurable.get("citation_style", "IEEE")
    
    if citation_style == "APA":
        citation_instruction = "Use APA in-text citations, e.g., (Author, Year). Do not use [1], [2]."
    else:
        citation_instruction = "Use IEEE numeric citations, e.g., [1], [2]. Ensure numbers correspond to the provided source list."

    prompt = f"""
    You are a technical researcher. Write a detailed report on: {state['task']}
    
    Use the following research notes:
    {context_string}
    
    {citation_instruction}
    
    IMPORTANT: Do NOT include a "References" or "Bibliography" section at the end of your report. 
    The system will handle the bibliography display separately.
    
    Return ONLY the report content.
    """

    response = llm.invoke(prompt)
    print(f"DEBUG: Writer produced draft (starts with): {response.content[:200]}...")
    return {
        "draft": response.content,
        "revision_number": state.get("revision_number", 0) + 1
    }

def critique_node(state: AgentState, config):
    """
    Critique Agent: Reviews the draft and provides feedback + next action.
    """
    print("--- Critique Node Running ---")
    
    llm = get_llm(config)
    
    configurable = config.get("configurable", {})
    max_revisions = configurable.get("max_revisions", 2)

    revision_number = state.get("revision_number", 0)
    if revision_number > max_revisions:
        print("DEBUG: Max revisions reached, skipping critique.")
        return {
            "critique": "Max revisions reached. Auto-approved.",
            "last_action": "APPROVE"
        }
    
    if not state.get("draft"):
        return {
            "critique": "No draft found.",
            "last_action": "REWRITE"
        }
    
    prompt = f"""
    You are a strict editor. Review this draft:
    {state['draft']}
    
    Critique strictness: High.
    
    Decide between these actions:
    - "APPROVE": If the draft is excellent and complete.
    - "RESEARCH_MORE": If the draft is missing crucial facts or citations.
    - "REWRITE": If the facts are there but the writing style/structure needs work.
    
    Return ONLY a JSON object:
    {{
        "critique": "Your specific feedback here...",
        "action": "APPROVE" | "RESEARCH_MORE" | "REWRITE"
    }}
    """

    response = llm.invoke(prompt)
    print(f"DEBUG: Critique raw response: {response.content}")
    try:
        content = response.content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        critique_text = result.get("critique", "No critique provided.")
        action = result.get("action", "REWRITE")
    except Exception:
        critique_text = response.content
        action = "REWRITE"

    return {
        "critique": critique_text,
        "last_action": action
    }

def should_continue(state: AgentState):
    """
    Decides the next node based on Critic's action
    """    
    revision_number = state.get("revision_number", 0)
    last_action = state.get("last_action", "REWRITE")
    
    print(f"DECISION: {last_action} (Rev: {revision_number})")

    if last_action == "APPROVE":
        return END
        
    if last_action == "RESEARCH_MORE":
        return "researcher"
    
    # Default: REWRITE
    return "writer"

workflow = StateGraph(AgentState)

workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)
workflow.add_node("critique", critique_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "critique")
workflow.add_conditional_edges(
    "critique",
    should_continue,
    {
        END: END, 
        "researcher": "researcher",
        "writer": "writer"
    }
)

app_graph = workflow.compile()