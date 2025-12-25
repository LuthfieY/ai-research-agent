import os
import json
from typing import List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults 

from app.agent_types import AgentState

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

tavily = TavilySearchResults(max_results=3)


def researcher_node(state: AgentState):
    """
    Research Agent: Generates search queries based on task/critique and executes them.
    """
    print("--- Researcher Node Running ---")
    task = state["task"]
    critique = state.get("critique")
    
    if critique:
        prompt = f"""
        You are a researcher. 
        User Task: {task}
        Critique on previous draft: {critique}
        
        Generate 2 specific search queries to gather missing information addressed in the critique.
        Return ONLY a JSON list of strings, e.g., ["query1", "query2"].
        """
    else:
        prompt = f"""
        You are a researcher. 
        User Task: {task}
        
        Generate 3 broad search queries to start researching this topic.
        Return ONLY a JSON list of strings, e.g., ["query1", "query2", "query3"].
        """
        
    response = llm.invoke(prompt)
    try:
        content = response.content.replace("```json", "").replace("```", "").strip()
        queries = json.loads(content)
    except Exception as e:
        print(f"JSON Parsing failed: {e}. Fallback to original task.")
        queries = [task]

    print(f"Searching for: {queries}")
    
    clean_results: List[ResearchResult] = []

    for q in queries:
        try:
            search_results = tavily.invoke(q)
            if search_results and isinstance(search_results, list):
                for result in search_results:
                    # Extract Year from published_date if available
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
            print(f"Error searching for {q}: {e}")
            
    print(f"DEBUG: Researcher found {len(clean_results)} results")
    return {"content": clean_results}

def writer_node(state: AgentState):
    """
    Writer Agent: Formats the structured data into a prompt.
    """
    print("--- Writer Node Running ---")
    
    context_string = ""
    if not state.get("content"):
        return {
            "draft": "Sorry, I could not find any relevant information to write a report.",
            "revision_number": state.get("revision_number", 0) + 1
        }

    for i, result in enumerate(state["content"], 1):
        context_string += f"[{i}] {result['title']} ({result['year']})\nSource: {result['source']}\nContent: {result['content']}\n\n"
    
    prompt = f"""
    You are a technical researcher. Write a detailed report on: {state['task']}
    
    Use the following research notes (include citations like [1], [2] where possible):
    {context_string}

    Return ONLY the report.
    """

    response = llm.invoke(prompt)
    print(f"DEBUG: Writer produced draft (starts with): {response.content[:200]}...")
    return {
        "draft": response.content,
        "revision_number": state.get("revision_number", 0) + 1
    }

def critique_node(state: AgentState):
    """
    Critique Agent: Reviews the draft and provides feedback + next action.
    """
    print("--- Critique Node Running ---")
    
    revision_number = state.get("revision_number", 0)
    if revision_number > 1:
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