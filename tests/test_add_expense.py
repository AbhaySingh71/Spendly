"""
Tests for Step 7: Add Expense

This feature adds a form at /expenses/add that allows logged-in users to submit
new expenses with: amount, category, date, and optional description.

Tests verify:
- Authentication guards on both GET and POST
- Form renders with all required fields and category options
- Valid submissions redirect to profile and insert into DB
- Validation errors for missing/invalid fields
- Optional description field handling
"""

import pytest
from datetime import date
from app import app as flask_app
from database.db import init_db, create_user, get_db, insert_expense


@pytest.fixture
def app():
    """Create test Flask app with in-memory database."""
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        init_db()
        # Create test user
        user_id = create_user("Test User", "test@example.com", "password123")
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client that is logged in."""
    client.post('/login', data={'email': 'test@example.com', 'password': 'password123'})
    return client


class TestInsertExpenseUnit:
    """Unit tests for insert_expense database helper function."""

    def test_insert_expense_with_all_fields(self, app):
        """Insert expense with all fields and verify it exists in DB."""
        user_id = create_user("User Two", "user2@example.com", "password123")

        expense_id = insert_expense(
            user_id,
            50.0,
            "Food",
            "2026-03-20",
            "Lunch"
        )

        # Query DB to verify insertion
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT user_id, amount, category, date, description FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cur.fetchone()
        db.close()

        assert row is not None, "Expense should be inserted"
        assert row["user_id"] == user_id
        assert row["amount"] == 50.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-20"
        assert row["description"] == "Lunch"

    def test_insert_expense_with_null_description(self, app):
        """Insert expense with description=None should store NULL."""
        user_id = create_user("User Three", "user3@example.com", "password123")

        expense_id = insert_expense(
            user_id,
            100.0,
            "Transport",
            "2026-05-01",
            None
        )

        # Query DB to verify description is NULL
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT description FROM expenses WHERE id = ?",
            (expense_id,)
        )
        row = cur.fetchone()
        db.close()

        assert row is not None, "Expense should be inserted"
        assert row["description"] is None, "Description should be NULL when not provided"


class TestAuthGuard:
    """Tests for authentication protection on /expenses/add route."""

    def test_get_expenses_add_without_login_redirects_to_login(self, client):
        """GET /expenses/add without login should redirect to /login."""
        response = client.get('/expenses/add')
        assert response.status_code == 302, "Should redirect"
        assert '/login' in response.location, "Should redirect to login page"

    def test_post_expenses_add_without_login_redirects_to_login(self, client):
        """POST /expenses/add without login should redirect to /login."""
        response = client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': '2026-05-01'
        })
        assert response.status_code == 302, "Should redirect"
        assert '/login' in response.location, "Should redirect to login page"


class TestGetAddExpenseForm:
    """Tests for GET /expenses/add when authenticated."""

    def test_get_expenses_add_authenticated_returns_200(self, auth_client):
        """GET /expenses/add as logged-in user should return 200."""
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200, "Authenticated request should succeed"

    def test_get_expenses_add_form_contains_category_select(self, auth_client):
        """Form should contain a category select dropdown."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode('utf-8')
        assert '<select' in data, "Should have a select element"
        assert 'category' in data, "Select should be for category field"

    def test_get_expenses_add_form_contains_all_seven_categories(self, auth_client):
        """Category dropdown should have all 7 valid categories."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode('utf-8')

        expected_categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        for cat in expected_categories:
            assert cat in data, f"Category '{cat}' should be in dropdown options"

    def test_get_expenses_add_form_has_post_method(self, auth_client):
        """Form should use POST method."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode('utf-8')
        assert 'method="POST"' in data or "method='POST'" in data, "Form should use POST"

    def test_get_expenses_add_form_has_amount_field(self, auth_client):
        """Form should have amount input field."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode('utf-8')
        assert 'amount' in data, "Form should have amount field"

    def test_get_expenses_add_form_has_date_field(self, auth_client):
        """Form should have date input field."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode('utf-8')
        assert 'date' in data, "Form should have date field"


class TestPostAddExpenseValid:
    """Tests for POST /expenses/add with valid data."""

    def test_post_valid_expense_redirects_to_profile(self, auth_client):
        """Submitting valid expense should redirect to /profile."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })
        assert response.status_code == 302, "Should redirect after successful submission"
        assert '/profile' in response.location, "Should redirect to profile page"

    def test_post_valid_expense_inserts_into_database(self, auth_client):
        """Valid submission should insert expense into database."""
        # Get initial count
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM expenses WHERE user_id = 1")
        initial_count = cur.fetchone()["cnt"]
        db.close()

        # Submit expense
        auth_client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        # Verify new expense exists
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM expenses WHERE user_id = 1")
        final_count = cur.fetchone()["cnt"]
        cur.execute("SELECT amount, category, date, description FROM expenses WHERE user_id = 1 ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        db.close()

        assert final_count == initial_count + 1, "Should have one more expense"
        assert row["amount"] == 50.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-20"
        assert row["description"] == "Lunch"

    def test_post_expense_without_description_redirects_to_profile(self, auth_client):
        """Submitting expense without optional description should succeed."""
        response = auth_client.post('/expenses/add', data={
            'amount': '100.0',
            'category': 'Transport',
            'date': '2026-05-01',
            'description': ''
        })
        assert response.status_code == 302, "Should redirect"
        assert '/profile' in response.location

    def test_post_expense_without_description_stores_null(self, auth_client):
        """Expense without description should have NULL in database."""
        # Submit without description
        auth_client.post('/expenses/add', data={
            'amount': '100.0',
            'category': 'Transport',
            'date': '2026-05-01',
            'description': ''
        })

        # Check DB
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT description FROM expenses WHERE user_id = 1 ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        db.close()

        assert row is not None, "Expense should be inserted"
        assert row["description"] is None, "Description should be NULL for empty string"


class TestPostAddExpenseValidation:
    """Tests for POST /expenses/add validation errors."""

    def test_post_missing_amount_returns_200_with_error(self, auth_client):
        """Missing amount should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'amount' in data.lower(), "Should show error for amount"

    def test_post_zero_amount_returns_200_with_error(self, auth_client):
        """Amount of 0 should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'amount' in data.lower(), "Should show error for amount"

    def test_post_negative_amount_returns_200_with_error(self, auth_client):
        """Negative amount should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '-50',
            'category': 'Food',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'amount' in data.lower(), "Should show error for amount"

    def test_post_non_numeric_amount_returns_200_with_error(self, auth_client):
        """Non-numeric amount should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'amount' in data.lower() or 'valid' in data.lower(), "Should show error"

    def test_post_missing_category_returns_200_with_error(self, auth_client):
        """Missing category should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': '',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'category' in data.lower(), "Should show error for category"

    def test_post_invalid_category_returns_200_with_error(self, auth_client):
        """Invalid category not in list should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'InvalidCategory',
            'date': '2026-05-01'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'category' in data.lower(), "Should show error for category"

    def test_post_missing_date_returns_200_with_error(self, auth_client):
        """Missing date should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': ''
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'date' in data.lower(), "Should show error for date"

    def test_post_invalid_date_format_returns_200_with_error(self, auth_client):
        """Invalid date format should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': 'not-a-date'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'date' in data.lower() or 'valid' in data.lower(), "Should show error for date"

    def test_post_invalid_date_wrong_format_returns_200_with_error(self, auth_client):
        """Date in wrong format (e.g., MM/DD/YYYY) should return form with error."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': '05/01/2026'
        })
        assert response.status_code == 200, "Should re-render form"
        data = response.data.decode('utf-8')
        assert 'date' in data.lower() or 'valid' in data.lower(), "Should show error for date"


class TestValidationErrorRepopulates:
    """Tests that validation errors re-populate form fields."""

    def test_validation_error_repopulates_amount(self, auth_client):
        """On validation error, previously entered amount should be re-populated."""
        response = auth_client.post('/expenses/add', data={
            'amount': '123.45',
            'category': '',
            'date': '2026-05-01'
        })
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        assert '123.45' in data, "Amount should be re-populated in form"

    def test_validation_error_repopulates_category(self, auth_client):
        """On validation error, previously entered category should be re-populated."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': ''
        })
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        assert 'Food' in data, "Category should be re-populated in form"

    def test_validation_error_repopulates_date(self, auth_client):
        """On validation error, previously entered date should be re-populated."""
        response = auth_client.post('/expenses/add', data={
            'amount': '50',
            'category': 'Food',
            'date': '2026-03-15'
        })
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        assert '2026-03-15' in data, "Date should be re-populated in form"

    def test_validation_error_repopulates_description(self, auth_client):
        """On validation error, previously entered description should be re-populated."""
        response = auth_client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-05-01',
            'description': 'Test description'
        })
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        assert 'Test description' in data, "Description should be re-populated in form"