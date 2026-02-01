import json
from typing import Optional
from .db import get_db_connection

def create_session(session_id: str, parent_session_id: Optional[str] = None):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sessions (session_id, parent_session_id) VALUES (?, ?)", (session_id, parent_session_id))
        conn.commit()
        return True
    except Exception:
        # Session likely exists
        return False
    finally:
        conn.close()

def list_sessions():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Get all sessions with their last message time if possible, or just IDs
        # For simplicity, just listing IDs for now.
        c.execute("SELECT session_id, created_at FROM sessions ORDER BY created_at DESC")
        rows = c.fetchall()
        return [{"session_id": row["session_id"], "created_at": row["created_at"]} for row in rows]
    except Exception:
        return []
    finally:
        conn.close()

def add_message(session_id: str, message: dict):
    """
    Store a message in the database.
    message: dict with 'role', 'content', and optional 'tool_calls', 'tool_call_id', 'name'
    """
    # De-duplication: don't add the exact same message if it's already the latest in history
    # This prevents double-storage when both main.py and agent.py try to save.
    conn = get_db_connection()
    c = conn.cursor()
    
    role = message.get("role")
    content = message.get("content")
    tool_call_id = message.get("tool_call_id")
    name = message.get("name")

    # Check last message
    c.execute('''
        SELECT role, content, tool_call_id, name FROM messages 
        WHERE session_id = ? 
        ORDER BY id DESC LIMIT 1
    ''', (session_id,))
    last = c.fetchone()
    if last:
        if (last["role"] == role and 
            last["content"] == content and 
            last["tool_call_id"] == tool_call_id and 
            last["name"] == name):
            conn.close()
            return

    # Handle tool calls serialization
    tool_calls = None
    if message.get("tool_calls"):
        tool_calls = json.dumps([
            {
                "id": tc.id if hasattr(tc, 'id') else tc.get('id'),
                "type": tc.type if hasattr(tc, 'type') else tc.get('type'),
                "function": {
                    "name": tc.function.name if hasattr(tc, 'function') else tc.get('function').get('name'),
                    "arguments": tc.function.arguments if hasattr(tc, 'function') else tc.get('function').get('arguments')
                }
            }
            for tc in message.get("tool_calls")
        ])
    
    c.execute('''
        INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, role, content, tool_calls, tool_call_id, name))
    
    conn.commit()
    conn.close()

def get_session_history(session_id: str, limit: int = 20):
    """
    Retrieve message history for a session.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get last N messages ordered by time
    c.execute('''
        SELECT role, content, tool_calls, tool_call_id, name 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY id ASC
    ''', (session_id,))
    
    rows = c.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        msg = {
            "role": row["role"],
            "content": row["content"]
        }
        if row["tool_calls"]:
            msg["tool_calls"] = json.loads(row["tool_calls"])
        if row["tool_call_id"]:
            msg["tool_call_id"] = row["tool_call_id"]
        if row["name"]:
            msg["name"] = row["name"]
            
        messages.append(msg)
        
    return messages

def reset_session(session_id: str):
    """
    Clear all messages for a given session.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
