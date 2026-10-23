import sqlite3
import os

def init_db():
    print("Initializing Enterprise Database Schema...")
    conn = sqlite3.connect("datascout.db")
    cursor = conn.cursor()

    # Documents Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size TEXT,
            upload_date TEXT,
            status TEXT DEFAULT 'pending',
            entities_count INTEGER DEFAULT 0
        )
    """)

    # Agent Activity Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            query TEXT,
            status TEXT,
            timestamp TEXT,
            duration_ms INTEGER
        )
    """)

    # Ensure query_audit exists (created by SQL agent, but good to ensure)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            query TEXT,
            result TEXT
        )
    """)

    # Custom Agents
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default settings if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO user_settings (key, value) VALUES
        ('openai_model', 'gpt-4o'),
        ('theme', 'dark'),
        ('notifications', 'true'),
        ('auto_save', 'true')
    """)

    conn.commit()
    conn.close()
    print("[OK] Database initialized with Enterprise tables.")

    # Initialize relational business schema
    from db_schema import init_relational_schema
    init_relational_schema()

if __name__ == "__main__":
    init_db()
