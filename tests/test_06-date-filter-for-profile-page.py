"""
Tests for Step 6: Date Filter for Profile Page

This feature adds a date-range filter to the /profile route with:
- Quick-select presets: This Month, Last 3 Months, Last 6 Months, All Time
- Custom date range inputs
- Filter affects summary stats, transactions, and category breakdown
"""

import pytest
from datetime import date, timedelta
from app import app as flask_app
from database.db import init_db, create_user


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
        # Create test user with known expenses
        user_id = create_user("Test User", "test@example.com", "password123")
        # Add expenses in different months
        db = None
        from database.db import get_db
        db = get_db()
        today = date.today()
        # Current month expense
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 100, "Food", today.strftime("%Y-%m-%d"), "Current month")
        )
        # 2 months ago
        two_months_ago = today - timedelta(days=60)
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 200, "Transport", two_months_ago.strftime("%Y-%m-%d"), "2 months ago")
        )
        # 5 months ago
        five_months_ago = today - timedelta(days=150)
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 300, "Bills", five_months_ago.strftime("%Y-%m-%d"), "5 months ago")
        )
        # 8 months ago (should be outside last 6 months)
        eight_months_ago = today - timedelta(days=240)
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 400, "Shopping", eight_months_ago.strftime("%Y-%m-%d"), "8 months ago")
        )
        db.commit()
        if db:
            db.close()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client that is logged in."""
    client.post('/login', data={'email': 'test@example.com', 'password': 'password123'})
    return client


class TestAuthGuard:
    """Tests for authentication protection on /profile route."""

    def test_get_profile_without_login_redirects_to_login(self, client):
        """GET /profile without login should redirect to /login."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location


class TestUnfilteredView:
    """Tests for /profile without any date filter."""

    def test_profile_no_params_returns_all_expenses(self, auth_client):
        """GET /profile with no date params returns all expenses (unfiltered)."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should contain all 4 expenses (100 + 200 + 300 + 400 = 1000)
        assert '1000' in data or '1,000' in data  # total spent

    def test_profile_no_params_shows_all_transactions(self, auth_client):
        """Without filter, all transactions should appear."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should see descriptions from all expenses
        assert 'Current month' in data
        assert '2 months ago' in data
        assert '5 months ago' in data
        assert '8 months ago' in data


class TestPresetFilters:
    """Tests for quick-select preset buttons."""

    def test_this_month_filter(self, auth_client):
        """Clicking 'This Month' filters to current month only."""
        today = date.today()
        this_month_start = date(today.year, today.month, 1).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={this_month_start}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show only current month expense (100)
        assert '100' in data
        # Should NOT show older expenses
        assert '2 months ago' not in data

    def test_last_3_months_filter(self, auth_client):
        """Clicking 'Last 3 Months' filters to last 3 months."""
        today = date.today()
        three_months_ago = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={three_months_ago}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show current month + 2 months ago = 100 + 200 = 300
        assert '300' in data
        # Should NOT show 5 months ago or 8 months ago
        assert '5 months ago' not in data

    def test_last_6_months_filter(self, auth_client):
        """Clicking 'Last 6 Months' filters to last 6 months."""
        today = date.today()
        six_months_ago = (today - timedelta(days=180)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={six_months_ago}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show current month + 2 months ago + 5 months ago = 100 + 200 + 300 = 600
        assert '600' in data
        # Should NOT show 8 months ago
        assert '8 months ago' not in data

    def test_all_time_preset_removes_filter(self, auth_client):
        """Clicking 'All Time' should show all expenses (no query params)."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show total of all 4 expenses = 1000
        assert '1000' in data or '1,000' in data


class TestCustomDateRange:
    """Tests for custom date range submission."""

    def test_custom_range_shows_filtered_data(self, auth_client):
        """Custom date range submission shows filtered data."""
        today = date.today()
        # Custom range: last 30 days (should include current month)
        thirty_days_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={thirty_days_ago}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show current month expense only
        assert '100' in data

    def test_custom_range_filters_transactions(self, auth_client):
        """Custom range should filter transaction list."""
        today = date.today()
        # Range that includes only 2 months ago
        start = (today - timedelta(days=70)).strftime("%Y-%m-%d")
        end = (today - timedelta(days=50)).strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={start}&date_to={end}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should show 2 months ago expense
        assert '2 months ago' in data
        # Should NOT show other expenses
        assert 'Current month' not in data


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_start_date_greater_than_end_date(self, auth_client):
        """start_date > end_date shows flash error and falls back to unfiltered."""
        response = auth_client.get('/profile?date_from=2025-12-31&date_to=2025-01-01')
        assert response.status_code == 200
        # Should show flash error message
        data = response.data.decode('utf-8')
        assert 'Start date must be before end date' in data
        # Should fall back to showing all expenses (1000 total)
        assert '1000' in data or '1,000' in data

    def test_malformed_date_from_does_not_crash(self, auth_client):
        """Malformed date string doesn't crash (falls back to unfiltered)."""
        response = auth_client.get('/profile?date_from=not-a-date&date_to=2025-05-15')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should fall back to showing all expenses
        assert '1000' in data or '1,000' in data

    def test_malformed_date_to_does_not_crash(self, auth_client):
        """Malformed date_to doesn't crash (falls back to unfiltered)."""
        response = auth_client.get('/profile?date_from=2025-01-01&date_to=invalid')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should fall back to showing all expenses
        assert '1000' in data or '1,000' in data

    def test_user_with_no_expenses_in_range_sees_zero_totals(self, auth_client):
        """User with no expenses in date range sees 0 totals."""
        # Create new user with no expenses
        from database.db import get_db
        db = get_db()
        user_id = create_user("Empty User", "empty@example.com", "password123")
        db.close()

        # Login as empty user
        client = flask_app.test_client()
        with flask_app.app_context():
            client.post('/login', data={'email': 'empty@example.com', 'password': 'password123'})

            # Try any date filter
            today = date.today()
            response = client.get(f'/profile?date_from={today.strftime("%Y-%m-%d")}&date_to={today.strftime("%Y-%m-%d")}')
            assert response.status_code == 200
            data = response.data.decode('utf-8')
            # Should show 0 total spent
            assert '0' in data or '₹0' in data or '0.00' in data


class TestDataIntegrity:
    """Tests for data integrity with filters."""

    def test_summary_stats_update_with_filter(self, auth_client):
        """Summary stats (total_spent, transactions, top_category) update based on filter."""
        today = date.today()
        six_months_ago = (today - timedelta(days=180)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={six_months_ago}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Total should be 600 (100 + 200 + 300)
        assert '600' in data

    def test_transaction_list_updates_with_filter(self, auth_client):
        """Transaction list updates based on filter."""
        today = date.today()
        this_month_start = date(today.year, today.month, 1).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        response = auth_client.get(f'/profile?date_from={this_month_start}&date_to={today_str}')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Only current month transaction should appear
        assert 'Current month' in data
        # Others should not appear
        assert '2 months ago' not in data

    def test_rupee_symbol_still_displays(self, auth_client):
        """Rupee symbol still displays regardless of filter."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should contain the ₹ symbol
        assert '₹' in data


class TestFilterBarPresence:
    """Tests to verify filter bar elements are present in the template."""

    def test_profile_template_has_filter_inputs(self, auth_client):
        """Profile page should have date filter inputs."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should have date input fields
        assert 'date_from' in data or 'type="date"' in data

    def test_profile_template_has_preset_buttons(self, auth_client):
        """Profile page should have preset filter buttons."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        # Should have This Month, Last 3 Months, Last 6 Months, All Time
        assert 'This Month' in data or 'this_month' in data.lower()
        assert 'Last 3 Months' in data or 'last_3_months' in data.lower()
        assert 'Last 6 Months' in data or 'last_6_months' in data.lower()
        assert 'All Time' in data