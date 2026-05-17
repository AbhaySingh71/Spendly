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
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
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
            (user_id, amount, cat, date, desc),
        )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    cur = conn.cursor()
    password_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)
    )
    user = cur.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
    )
    user = cur.fetchone()
    conn.close()
    if user:
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "member_since": format_member_date(user["created_at"]),
        }
    return None


def format_member_date(date_str):
    if not date_str:
        return "Unknown"
    try:
        from datetime import datetime

        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %Y")
    except Exception:
        return date_str


def build_date_filter(start_date=None, end_date=None):
    """Build date filter SQL clause and params list."""
    params = []
    date_filter = ""
    if start_date and end_date:
        date_filter = "AND date BETWEEN ? AND ?"
        params = [start_date, end_date]
    elif start_date:
        date_filter = "AND date >= ?"
        params = [start_date]
    elif end_date:
        date_filter = "AND date <= ?"
        params = [end_date]
    return date_filter, params


def get_user_expenses(user_id, start_date=None, end_date=None):
    conn = get_db()
    cur = conn.cursor()

    date_filter, date_params = build_date_filter(start_date, end_date)
    params = [user_id] + date_params

    cur.execute(
        f"""
        SELECT id, date, description, category, amount
        FROM expenses
        WHERE user_id = ? {date_filter}
        ORDER BY date DESC
        LIMIT 10
    """,
        params,
    )
    rows = cur.fetchall()
    conn.close()

    expenses = []
    for row in rows:
        expenses.append(
            {
                "id": row["id"],
                "date": format_expense_date(row["date"]),
                "description": row["description"] or "",
                "category": row["category"],
                "amount": row["amount"],
            }
        )
    return expenses


def format_expense_date(date_str):
    if not date_str:
        return ""
    try:
        from datetime import datetime

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d")
    except Exception:
        return date_str


def get_user_stats(user_id, start_date=None, end_date=None):
    conn = get_db()
    cur = conn.cursor()

    date_filter, date_params = build_date_filter(start_date, end_date)

    params = [user_id] + date_params
    cur.execute(
        f"SELECT SUM(amount) as total FROM expenses WHERE user_id = ? {date_filter}",
        params,
    )
    total_row = cur.fetchone()
    total_spent = int(total_row["total"]) if total_row["total"] else 0

    params = [user_id] + date_params
    cur.execute(
        f"SELECT COUNT(*) as cnt FROM expenses WHERE user_id = ? {date_filter}", params
    )
    count_row = cur.fetchone()
    transactions = count_row["cnt"] if count_row["cnt"] else 0

    params = [user_id] + date_params
    cur.execute(
        f"""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? {date_filter}
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """,
        params,
    )
    top_row = cur.fetchone()
    top_category = top_row["category"] if top_row else "None"

    conn.close()

    return {
        "total_spent": total_spent,
        "transactions": transactions,
        "top_category": top_category,
    }


def insert_expense(user_id, amount, category, date, description=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    expense_id = cur.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, amount, category, date, description
        FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (expense_id, user_id),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "amount": row["amount"],
            "category": row["category"],
            "date": row["date"],
            "description": row["description"] or "",
        }
    return None


def update_expense(expense_id, user_id, amount, category, date, description=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE expenses
        SET amount = ?, category = ?, date = ?, description = ?
        WHERE id = ? AND user_id = ?
        """,
        (amount, category, date, description, expense_id, user_id),
    )
    conn.commit()
    conn.close()
