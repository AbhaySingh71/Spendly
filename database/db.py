import sqlite3
from werkzeug.security import generate_password_hash

DATABASE_PATH = "spendly.db"


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.close()


def seed_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users LIMIT 1")
    if cur.fetchone():
        conn.close()
        return

    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123"))
    )
    user_id = cur.lastrowid

    expenses = [
        (250, "Food", "2025-05-01", "Breakfast at Cafe"),
        (45, "Transport", "2025-05-03", "Uber ride"),
        (1200, "Bills", "2025-05-05", "Electricity bill"),
        (500, "Health", "2025-05-07", "Pharmacy"),
        (200, "Entertainment", "2025-05-09", "Movie tickets"),
        (800, "Shopping", "2025-05-11", "Groceries"),
        (150, "Food", "2025-05-10", "Lunch with friends"),
        (60, "Transport", "2025-05-12", "Bus pass"),
    ]
    for amount, cat, date, desc in expenses:
        cur.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, cat, date, desc)
        )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    cur = conn.cursor()
    password_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash)
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user