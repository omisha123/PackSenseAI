import sqlite3
import hashlib
import json
from datetime import datetime

DB_NAME = "packaging_app.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Create Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # Create History table
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  commodity TEXT,
                  language TEXT,
                  recommendation TEXT,
                  roi_data TEXT,
                  trace_data TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()

    # Migrate older databases that predate roi_data/trace_data columns
    c.execute("PRAGMA table_info(history)")
    existing_cols = {row[1] for row in c.fetchall()}
    if "roi_data" not in existing_cols:
        c.execute("ALTER TABLE history ADD COLUMN roi_data TEXT")
    if "trace_data" not in existing_cols:
        c.execute("ALTER TABLE history ADD COLUMN trace_data TEXT")
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return check_hashes(password, data[0])
    return False

def save_recommendation(username, commodity, language, recommendation, roi_data=None, trace_data=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        '''INSERT INTO history (username, commodity, language, recommendation, roi_data, trace_data)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (
            username,
            commodity,
            language,
            recommendation,
            json.dumps(roi_data) if roi_data is not None else None,
            json.dumps(trace_data) if trace_data is not None else None,
        )
    )
    conn.commit()
    conn.close()

def get_history(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        '''SELECT commodity, language, recommendation, timestamp, roi_data, trace_data
           FROM history WHERE username = ? ORDER BY timestamp DESC''',
        (username,)
    )
    rows = c.fetchall()
    conn.close()

    result = []
    for commodity, language, recommendation, timestamp, roi_json, trace_json in rows:
        try:
            roi_data = json.loads(roi_json) if roi_json else None
        except (TypeError, ValueError):
            roi_data = None
        try:
            trace_data = json.loads(trace_json) if trace_json else None
        except (TypeError, ValueError):
            trace_data = None
        result.append((commodity, language, recommendation, timestamp, roi_data, trace_data))
    return result