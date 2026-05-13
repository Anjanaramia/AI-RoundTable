# ──────────────────────────────────────────────────────────────────────
# database.py — AI RoundTable persistence layer (SQLite)
# ──────────────────────────────────────────────────────────────────────
#
# ⚠️  IMPORTANT — STATELESS CLOUD DEPLOYMENTS  ⚠️
# ──────────────────────────────────────────────────────────────────────
# SQLite stores data in a local file (users.db).  On stateless hosting
# platforms — Streamlit Cloud, Railway, Render, Fly.io — the filesystem
# is ephemeral.  Every redeploy or cold-start RESETS the database.
#
# Migration path to a persistent backend:
#   1. Supabase (easiest):
#      - Create a free project at https://supabase.com
#      - Use the supabase-py client: `from supabase import create_client`
#      - Replace every sqlite3 call with Supabase table operations.
#
#   2. PostgreSQL via psycopg2:
#      - Provision a Postgres instance (Supabase, Neon, Railway, etc.)
#      - pip install psycopg2-binary
#      - Replace sqlite3.connect(DB_FILE) with:
#            psycopg2.connect(os.environ["DATABASE_URL"])
#      - Adjust SQL syntax (e.g., SERIAL vs AUTOINCREMENT,
#        %s placeholders instead of ?).
#
# Until you migrate, treat users.db as a development convenience only.
# ──────────────────────────────────────────────────────────────────────

import sqlite3
from datetime import datetime
import pandas as pd

DB_FILE = "users.db"


def _get_conn():
    """Return a new connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)


# ── Schema Initialisation & Migration ────────────────────────────────

def init_db():
    """Create tables if they don't exist and run lightweight migrations."""
    conn = _get_conn()
    c = conn.cursor()

    # -- users table --
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            email             TEXT UNIQUE NOT NULL,
            name              TEXT,
            first_access_date TEXT NOT NULL,
            last_query_time   TEXT
        )
    """)

    # Migration: add last_query_time if upgrading from an older schema
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    if "last_query_time" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN last_query_time TEXT")

    # -- query_history table --
    c.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT NOT NULL,
            prompt     TEXT NOT NULL,
            synthesis  TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ── User Operations ──────────────────────────────────────────────────

def add_user(email: str, name: str = "") -> bool:
    """Insert a new user.  Returns False if the email already exists."""
    conn = _get_conn()
    c = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO users (email, name, first_access_date) VALUES (?, ?, ?)",
            (email, name, now_str),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # email already registered
    finally:
        conn.close()


def get_all_users() -> pd.DataFrame:
    """Return every user row as a DataFrame (admin dashboard)."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT email, name, first_access_date, last_query_time "
        "FROM users ORDER BY first_access_date DESC",
        conn,
    )
    conn.close()
    return df


# ── Rate-Limiting ────────────────────────────────────────────────────

def get_last_query_time(email: str) -> str | None:
    """Return the ISO-formatted last_query_time for *email*, or None."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT last_query_time FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None


def update_last_query_time(email: str) -> None:
    """Stamp the current time as the user's last_query_time."""
    conn = _get_conn()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "UPDATE users SET last_query_time = ? WHERE email = ?",
        (now_str, email),
    )
    conn.commit()
    conn.close()


# ── Query History ────────────────────────────────────────────────────

def save_query_history(email: str, prompt: str, synthesis: str) -> None:
    """Persist a completed query run."""
    conn = _get_conn()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO query_history (email, prompt, synthesis, created_at) "
        "VALUES (?, ?, ?, ?)",
        (email, prompt, synthesis, now_str),
    )
    conn.commit()
    conn.close()


def get_query_history(email: str, limit: int = 10) -> list[dict]:
    """Return the most recent *limit* query-history rows for *email*."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, email, prompt, synthesis, created_at "
        "FROM query_history WHERE email = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (email, limit),
    )
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "email": r[1],
            "prompt": r[2],
            "synthesis": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]
