from flask import (
    Flask,
    render_template,
    flash,
    redirect,
    request,
    url_for,
    abort,
    session,
)
import sqlite3
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "dev-secret-key-for-spendly"

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_expenses,
    get_user_stats,
    insert_expense,
)

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


def parse_date_filter(request_args):
    """Parse and validate date filter parameters from request."""
    date_from = request_args.get("date_from", "")
    date_to = request_args.get("date_to", "")
    active_filter = None
    start_date = None
    end_date = None

    if date_from or date_to:
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                date_from = ""

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                date_to = ""

        if date_from and date_to:
            if start_date > end_date:
                flash("Start date must be before end date.", "error")
                return "", "", None, None, None
            else:
                active_filter = "custom"
        elif date_from:
            start_date = date_from
            end_date = datetime.now().strftime("%Y-%m-%d")
            active_filter = "custom"
        elif date_to:
            end_date = date_to
            active_filter = "custom"

    return date_from, date_to, start_date, end_date, active_filter


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    date_from, date_to, start_date, end_date, active_filter = parse_date_filter(
        request.args
    )

    stats = get_user_stats(user_id, start_date, end_date)
    transactions = get_user_expenses(user_id, start_date, end_date)

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
        "Entertainment": "cyan",
    }

    max_amount = max(category_totals.values()) if category_totals else 1
    categories = []
    for name, amount in sorted(
        category_totals.items(), key=lambda x: x[1], reverse=True
    ):
        bar_width = int(round((amount / max_amount) * 100)) if max_amount > 0 else 0
        categories.append(
            {
                "name": name,
                "amount": amount,
                "color": color_map.get(name, "gray"),
                "bar_width": bar_width,
            }
        )

    today = date.today()
    this_month_start = date(today.year, today.month, 1).strftime("%Y-%m-%d")
    three_months_ago = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    six_months_ago = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    if date_from == this_month_start and date_to == today_str:
        active_filter = "this_month"
    elif date_from == three_months_ago and date_to == today_str:
        active_filter = "last_3_months"
    elif date_from == six_months_ago and date_to == today_str:
        active_filter = "last_6_months"

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        max_category_amount=max_amount,
        date_from=date_from,
        date_to=date_to,
        active_filter=active_filter,
        this_month_start=this_month_start,
        three_months_ago=three_months_ago,
        six_months_ago=six_months_ago,
        today=today_str,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        today = date.today().strftime("%Y-%m-%d")
        return render_template("add_expense.html", today=today)

    if request.method != "POST":
        abort(405)

    amount_str = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_val = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    errors = {}

    if not amount_str:
        errors["amount"] = "Amount is required"
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors["amount"] = "Amount must be greater than 0"
        except ValueError:
            errors["amount"] = "Please enter a valid number"

    valid_categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
    if not category:
        errors["category"] = "Category is required"
    elif category not in valid_categories:
        errors["category"] = "Invalid category"

    if not date_val:
        errors["date"] = "Date is required"
    else:
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            errors["date"] = "Please enter a valid date (YYYY-MM-DD)"

    if errors:
        return render_template(
            "add_expense.html",
            today=today,
            amount=amount_str,
            category=category,
            date=date_val,
            description=description,
            errors=errors,
        )

    user_id = session.get("user_id")
    insert_expense(user_id, amount, category, date_val, description or None)

    flash("Expense added successfully!", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
