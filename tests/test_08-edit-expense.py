"""
Tests for Step 8: Edit Expense

This feature adds an edit form at /expenses/<id>/edit that allows logged-in
users to update their own expenses. Tests cover auth guards, validation errors,
happy paths, and DB side effects.
"""

import re
from uuid import uuid4

import pytest
from flask import url_for

from app import app as flask_app
from database.db import (
    init_db,
    create_user,
    get_db,
    insert_expense,
    get_expense_by_id,
    update_expense,
)


VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


@pytest.fixture
def app():
    """Create test Flask app with a clean database."""
    flask_app.config.update({
        "TESTING": True,
        "DATABASE": ":memory:",
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        init_db()
        db = get_db()
        db.execute("DELETE FROM expenses")
        db.execute("DELETE FROM users")
        db.commit()
        db.close()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Test client that is logged in as a fresh user."""
    user_id, email, password = create_unique_user(app)
    login_client(app, client, email, password)
    return client


def create_unique_user(app, name="Test User"):
    email = f"{uuid4().hex}@example.com"
    password = "password123"
    with app.app_context():
        user_id = create_user(name, email, password)
    return user_id, email, password


def login_client(app, client, email, password):
    with app.test_request_context():
        login_url = url_for("login")
    client.post(login_url, data={"email": email, "password": password})


class TestGetExpenseByIdUnit:
    """Unit tests for get_expense_by_id helper."""

    def test_get_expense_by_id_returns_row_for_owner(self, app):
        with app.app_context():
            user_id, _, _ = create_unique_user(app)
            expense_id = insert_expense(
                user_id,
                50.0,
                "Food",
                "2026-05-01",
                "Lunch",
            )

            expense = get_expense_by_id(expense_id, user_id)

        assert expense is not None, "Expected an expense for the owning user"
        assert expense["id"] == expense_id
        assert expense["user_id"] == user_id
        assert expense["amount"] == 50.0
        assert expense["category"] == "Food"
        assert expense["date"] == "2026-05-01"
        assert expense["description"] == "Lunch"

    def test_get_expense_by_id_returns_none_for_wrong_user(self, app):
        with app.app_context():
            owner_id, _, _ = create_unique_user(app, name="Owner")
            other_id, _, _ = create_unique_user(app, name="Other")
            expense_id = insert_expense(
                owner_id,
                75.0,
                "Transport",
                "2026-06-10",
                "Taxi",
            )

            expense = get_expense_by_id(expense_id, other_id)

        assert expense is None, "Expected None for a non-owner user"

    def test_get_expense_by_id_returns_none_for_missing_id(self, app):
        with app.app_context():
            user_id, _, _ = create_unique_user(app)
            expense = get_expense_by_id(999999, user_id)

        assert expense is None, "Expected None for a non-existent expense"


class TestUpdateExpenseUnit:
    """Unit tests for update_expense helper."""

    def test_update_expense_updates_row_for_owner(self, app):
        with app.app_context():
            user_id, _, _ = create_unique_user(app)
            expense_id = insert_expense(
                user_id,
                25.0,
                "Bills",
                "2026-01-10",
                "Internet",
            )

            update_expense(
                expense_id,
                user_id,
                99.0,
                "Health",
                "2026-02-02",
                "Checkup",
            )

            db = get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT amount, category, date, description FROM expenses WHERE id = ?",
                (expense_id,),
            )
            row = cur.fetchone()
            db.close()

        assert row is not None, "Expected updated expense row"
        assert row["amount"] == 99.0
        assert row["category"] == "Health"
        assert row["date"] == "2026-02-02"
        assert row["description"] == "Checkup"

    def test_update_expense_does_not_update_for_wrong_user(self, app):
        with app.app_context():
            owner_id, _, _ = create_unique_user(app, name="Owner")
            other_id, _, _ = create_unique_user(app, name="Other")
            expense_id = insert_expense(
                owner_id,
                60.0,
                "Food",
                "2026-03-10",
                "Dinner",
            )

            update_expense(
                expense_id,
                other_id,
                120.0,
                "Shopping",
                "2026-03-12",
                "Shoes",
            )

            db = get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT amount, category, date, description FROM expenses WHERE id = ?",
                (expense_id,),
            )
            row = cur.fetchone()
            db.close()

        assert row is not None, "Expected original expense row to remain"
        assert row["amount"] == 60.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-10"
        assert row["description"] == "Dinner"


class TestEditExpenseAuthGuards:
    """Auth guard tests for edit expense routes."""

    def test_get_edit_expense_requires_login(self, app, client):
        with app.test_request_context():
            edit_url = url_for("edit_expense", id=1)
            login_url = url_for("login")

        response = client.get(edit_url)

        assert response.status_code == 302, "Expected redirect to login"
        assert response.headers["Location"].endswith(login_url)

    def test_post_edit_expense_requires_login(self, app, client):
        with app.test_request_context():
            edit_url = url_for("edit_expense", id=1)
            login_url = url_for("login")

        response = client.post(edit_url, data={
            "amount": "50",
            "category": "Food",
            "date": "2026-04-01",
        })

        assert response.status_code == 302, "Expected redirect to login"
        assert response.headers["Location"].endswith(login_url)


class TestEditExpenseGet:
    """GET /expenses/<id>/edit behavior."""

    def test_get_edit_expense_own_expense_prefills_form(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                123.45,
                "Food",
                "2026-05-20",
                "Cafe",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.get(edit_url)
        data = response.data.decode("utf-8")

        assert response.status_code == 200, "Expected edit form to load"
        assert "123.45" in data, "Amount should be pre-filled"
        assert "2026-05-20" in data, "Date should be pre-filled"
        assert "Cafe" in data, "Description should be pre-filled"
        assert re.search(r"<option[^>]*value=\"Food\"[^>]*selected", data), (
            "Expected category to be selected"
        )

    def test_get_edit_expense_other_user_returns_404(self, app, client):
        owner_id, _, _ = create_unique_user(app, name="Owner")
        other_id, other_email, other_password = create_unique_user(app, name="Other")
        with app.app_context():
            expense_id = insert_expense(
                owner_id,
                70.0,
                "Transport",
                "2026-01-15",
                "Bus",
            )

        login_client(app, client, other_email, other_password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.get(edit_url)

        assert response.status_code == 404, "Expected 404 for non-owner"

    def test_get_edit_expense_missing_id_returns_404(self, auth_client, app):
        with app.test_request_context():
            edit_url = url_for("edit_expense", id=999999)

        response = auth_client.get(edit_url)

        assert response.status_code == 404, "Expected 404 for missing expense"


class TestEditExpensePostValid:
    """POST /expenses/<id>/edit with valid data."""

    def test_post_edit_expense_valid_redirects_and_updates_db(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                40.0,
                "Bills",
                "2026-02-10",
                "Water",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)
            profile_url = url_for("profile")

        response = client.post(edit_url, data={
            "amount": "99.0",
            "category": "Health",
            "date": "2026-02-20",
            "description": "Checkup",
        })

        assert response.status_code == 302, "Expected redirect on success"
        assert response.headers["Location"].endswith(profile_url)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT amount, category, date, description FROM expenses WHERE id = ?",
                (expense_id,),
            )
            row = cur.fetchone()
            db.close()

        assert row is not None, "Expected updated expense in DB"
        assert row["amount"] == 99.0
        assert row["category"] == "Health"
        assert row["date"] == "2026-02-20"
        assert row["description"] == "Checkup"

    def test_post_edit_expense_without_description_stores_null(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                15.0,
                "Food",
                "2026-03-05",
                "Snack",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)
            profile_url = url_for("profile")

        response = client.post(edit_url, data={
            "amount": "15.0",
            "category": "Food",
            "date": "2026-03-05",
            "description": "",
        })

        assert response.status_code == 302, "Expected redirect on success"
        assert response.headers["Location"].endswith(profile_url)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT description FROM expenses WHERE id = ?", (expense_id,))
            row = cur.fetchone()
            db.close()

        assert row is not None, "Expected updated expense row"
        assert row["description"] is None, "Expected NULL description when empty"


class TestEditExpensePostValidation:
    """Validation error tests for POST /expenses/<id>/edit."""

    @pytest.mark.parametrize("amount", ["", "0", "abc"])
    def test_post_edit_expense_invalid_amount_re_renders_form(self, app, client, amount):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                10.0,
                "Food",
                "2026-04-10",
                "Breakfast",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.post(edit_url, data={
            "amount": amount,
            "category": "Food",
            "date": "2026-04-10",
            "description": "Breakfast",
        })
        data = response.data.decode("utf-8")

        assert response.status_code == 200, "Expected form re-render on error"
        assert "amount" in data.lower(), "Expected amount error message"

    def test_post_edit_expense_invalid_category_re_renders_form(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                20.0,
                "Transport",
                "2026-04-12",
                "Taxi",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.post(edit_url, data={
            "amount": "20.0",
            "category": "Invalid",
            "date": "2026-04-12",
            "description": "Taxi",
        })
        data = response.data.decode("utf-8")

        assert response.status_code == 200, "Expected form re-render on error"
        assert "category" in data.lower(), "Expected category error message"
        assert "20.0" in data, "Expected amount to be re-populated"
        assert "2026-04-12" in data, "Expected date to be re-populated"

    def test_post_edit_expense_invalid_date_re_renders_form(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                30.0,
                "Bills",
                "2026-04-20",
                "Water",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.post(edit_url, data={
            "amount": "30.0",
            "category": "Bills",
            "date": "not-a-date",
            "description": "Water",
        })
        data = response.data.decode("utf-8")

        assert response.status_code == 200, "Expected form re-render on error"
        assert "date" in data.lower(), "Expected date error message"

    def test_post_edit_expense_other_user_returns_404(self, app, client):
        owner_id, _, _ = create_unique_user(app, name="Owner")
        other_id, other_email, other_password = create_unique_user(app, name="Other")
        with app.app_context():
            expense_id = insert_expense(
                owner_id,
                55.0,
                "Shopping",
                "2026-04-25",
                "Shoes",
            )

        login_client(app, client, other_email, other_password)

        with app.test_request_context():
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.post(edit_url, data={
            "amount": "60.0",
            "category": "Shopping",
            "date": "2026-04-26",
            "description": "Shoes",
        })

        assert response.status_code == 404, "Expected 404 for non-owner"


class TestProfileEditLink:
    """Tests that profile page includes edit links for transactions."""

    def test_profile_transactions_include_edit_link(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                18.0,
                "Entertainment",
                "2026-05-11",
                "Movie",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            profile_url = url_for("profile")
            edit_url = url_for("edit_expense", id=expense_id)

        response = client.get(profile_url)
        data = response.data.decode("utf-8")

        assert response.status_code == 200, "Expected profile page to load"
        assert edit_url in data, "Expected edit link in transactions table"
