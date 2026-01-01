import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "research_history.db"

def init_db():
    """Initialize the SQLite database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            report TEXT,
            references_json TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_research(topic, report, references):
    """Save a research session to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # References should be a list of dicts, we serialize it to JSON string
    ref_json = json.dumps(references)
    c.execute('INSERT INTO history (topic, report, references_json) VALUES (?, ?, ?)', 
              (topic, report, ref_json))
    conn.commit()
    conn.close()

def delete_history_item(item_id):
    """Delete a history item by ID."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

def get_history():
    """Retrieve all history items ordered by newest first."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Allow accessing columns by name
    c = conn.cursor()
    c.execute('SELECT * FROM history ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    
    # Convert sqlite3.Row objects to dicts
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "topic": row["topic"],
            "report": row["report"],
            "references": json.loads(row["references_json"]),
            "timestamp": row["timestamp"]
        })
    return history
