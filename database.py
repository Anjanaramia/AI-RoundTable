import sqlite3
from datetime import datetime
import pandas as pd

DB_FILE = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            first_access_date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(email, name=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('INSERT INTO users (email, name, first_access_date) VALUES (?, ?, ?)', (email, name, now_str))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Email already exists
        return False
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT email, name, first_access_date FROM users ORDER BY first_access_date DESC", conn)
    conn.close()
    return df
