"""
Tests for Step 9: Delete Expense

Covers auth guards, ownership checks, POST-only behavior, and DB side effects.
"""

from uuid import uuid4

import pytest
from flask import url_for

from app import app as flask_app
from database.db import create_user, get_db, insert_expense, get_expense_by_id


@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "DATABASE": ":memory:",
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        db = get_db()
        db.execute("DELETE FROM expenses")
        db.execute("DELETE FROM users")
        db.commit()
        db.close()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


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


class TestDeleteExpenseAuth:
    def test_post_delete_requires_login(self, app, client):
        with app.test_request_context():
            delete_url = url_for("delete_expense", id=1)
            login_url = url_for("login")

        response = client.post(delete_url)

        assert response.status_code == 302
        assert response.headers["Location"].endswith(login_url)

    def test_get_delete_returns_405(self, app, client):
        user_id, email, password = create_unique_user(app)
        with app.app_context():
            expense_id = insert_expense(
                user_id,
                10.0,
                "Food",
                "2026-05-01",
                "Snack",
            )

        login_client(app, client, email, password)

        with app.test_request_context():
            delete_url = url_for("delete_expense", id=expense_id)

        response = client.get(delete_url)

        assert response.status_code == 405


class TestDeleteExpenseOwnership:
    def test_delete_other_user_returns_404(self, app, client):
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
            delete_url = url_for("delete_expense", id=expense_id)

        response = client.post(delete_url)

        assert response.status_code == 404

    def test_delete_missing_expense_returns_404(self, app, client):
        user_id, email, password = create_unique_user(app)
        login_client(app, client, email, password)

        with app.test_request_context():
            delete_url = url_for("delete_expense", id=999999)

        response = client.post(delete_url)

        assert response.status_code == 404


class TestDeleteExpenseSuccess:
    def test_delete_own_expense_redirects_and_removes_row(self, app, client):
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
            delete_url = url_for("delete_expense", id=expense_id)
            profile_url = url_for("profile")

        response = client.post(delete_url)

        assert response.status_code == 302
        assert response.headers["Location"].endswith(profile_url)

        with app.app_context():
            expense = get_expense_by_id(expense_id, user_id)

        assert expense is None


class TestProfileDeleteLink:
    def test_profile_shows_delete_action(self, app, client):
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
            delete_url = url_for("delete_expense", id=expense_id)

        response = client.get(profile_url)
        data = response.data.decode("utf-8")

        assert response.status_code == 200
        assert delete_url in data
