from .config import settings
import os
import sqlite3

def get_db_file():
    """Get the absolute path to the database file in WORK_DIR."""
    return os.path.join(settings.WORK_DIR, "liteclaw_memory.db")

def get_db_connection():
    db_file = get_db_file()
    # Create parent directory if missing (safety)
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            parent_session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if column exists (migration for existing db)
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN parent_session_id TEXT")
    except Exception:
        pass
    
    # Create messages table
    # Storing content as TEXT. For tool calls, we might serialize JSON.
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            tool_calls TEXT,
            tool_call_id TEXT,
            name TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    ''')

    # Create cron_jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS cron_jobs (
            id TEXT PRIMARY KEY,
            name TEXT,
            schedule_type TEXT,
            schedule_value TEXT,
            task TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_run TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize on module load
init_db()
