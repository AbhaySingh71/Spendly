from flask import Flask, render_template, flash, redirect, request, url_for, abort, session
import sqlite3

app = Flask(__name__)
app.secret_key = "dev-secret-key-for-spendly"

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, get_user_by_id, get_user_expenses, get_user_stats

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required", "error")
        return render_template("register.html")

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return render_template("register.html")

    if len(password) < 6:
        flash("Password must be at least 6 characters", "error")
        return render_template("register.html")

    try:
        create_user(name, email, password)
        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))
    except sqlite3.IntegrityError:
        flash("Email already registered", "error")
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Invalid email or password", "error")
        return render_template("login.html")

    user = get_user_by_email(email)

    if user is None:
        flash("Invalid email or password", "error")
        return render_template("login.html")

    from werkzeug.security import check_password_hash
    if not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password", "error")
        return render_template("login.html")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    stats = get_user_stats(user_id)
    transactions = get_user_expenses(user_id)

    category_totals = {}
    for tx in transactions:
        cat = tx["category"]
        category_totals[cat] = round(category_totals.get(cat, 0) + tx["amount"], 2)

    color_map = {
        "Food": "orange",
        "Transport": "blue",
        "Bills": "purple",
        "Health": "red",
        "Shopping": "green",
        "Entertainment": "cyan"
    }

    max_amount = max(category_totals.values()) if category_totals else 1
    categories = []
    for name, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        bar_width = int(round((amount / max_amount) * 100)) if max_amount > 0 else 0
        categories.append({
            "name": name,
            "amount": amount,
            "color": color_map.get(name, "gray"),
            "bar_width": bar_width
        })

    return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories, max_category_amount=max_amount)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
