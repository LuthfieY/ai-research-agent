import json
import os
from datetime import datetime
import uuid

HISTORY_FILE = "research_history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_to_history(task: str, final_state: dict):
    history = load_history()
    
    # Create simple record
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task": task,
        "draft": final_state.get("draft", ""),
        "content": final_state.get("content", []),
        "search_mode": final_state.get("search_mode", "Unknown"), # We might need to pass this if not in state anymore
        "citation_style": final_state.get("citation_style", "Unknown") # Same here
    }
    
    # Prepend to list (newest first)
    history.insert(0, record)
    
    # Keep max 10/20 records to save space? Let's keep 50.
    if len(history) > 50:
        history = history[:50]
        
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def delete_history_item(item_id):
    history = load_history()
    history = [h for h in history if h["id"] != item_id]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)
