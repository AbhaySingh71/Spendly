# Spec: Backend Routes for Profile Page

## Overview
This step connects the profile page (built in Step 4) to the database, replacing hardcoded data with real user data. The profile page will now display actual expenses, stats, and category breakdowns from the database.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)
- Step 4: Profile Page (template exists with hardcoded data)

## Routes
- GET /profile — render the profile page with real data — logged-in only (redirect to /login if not authenticated)

## Database changes
No new tables or columns needed. Use existing `users` and `expenses` tables.

## Templates
No new templates. Modify: `templates/profile.html` — no changes needed, template already expects correct variable names.

## Files to change
- `database/db.py` — add new functions to fetch user data and expenses
- `app.py` — update `/profile` route to use real database data instead of hardcoded dicts

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- New DB functions go in `database/db.py`, not in route functions
- Date formatting in Python before passing to template — don't format in Jinja

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays the logged-in user's actual name and email (from database)
- [ ] The page displays actual total spent from the database
- [ ] The page displays actual transaction count from the database
- [ ] The page displays actual top category from the database
- [ ] The transaction history table shows real expenses from the database
- [ ] The category breakdown shows real per-category totals from the database
- [ ] The navbar shows the logged-in user's actual name (from session)