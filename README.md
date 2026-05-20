# Spendly + Claude Code Development Harness

Spendly is a Flask + SQLite expense tracker, built as both a real app and a practical Claude Code workspace.
The app side focuses on simple, reliable personal finance tracking. The Claude side provides a structured AI engineering workflow: specs, reusable commands, specialist agents, skills, and deployment automation patterns.

Live app: https://spendly-flask-production.up.railway.app

## Project Screenshot
![Spendly Screenshot](assests/sp1.png)

## What Spendly Does
- User registration and login
- Session-based authentication
- Add, edit, and delete expenses
- Date-based filtering on profile view
- SQLite-backed persistence with lightweight architecture

## Tech Stack
- Backend: Flask
- Database: SQLite
- Frontend: Jinja templates + vanilla JS + plain CSS
- Tests: `pytest`, `pytest-flask`
- Production server: Gunicorn
- Hosting: Railway

## Repository Layout
```text
Spendly/
|- app.py
|- database/
|  |- __init__.py
|  `- db.py
|- templates/
|- static/
|  |- css/
|  `- js/
|- tests/
|- .claude/
|  |- agents/
|  |- commands/
|  |- skills/
|  |- specs/
|  |- launch.json
|  `- settings.local.json
|- Procfile
|- .railwayignore
|- requirements.txt
|- CLAUDE.md
`- README.md
```

## Local Development
1. Create virtual environment:
```bash
python -m venv venv
```
2. Activate:
```bash
# Windows (PowerShell)
venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Run app:
```bash
python app.py
```
5. Run tests:
```bash
pytest
```

Default local port: `5001`.

## Claude Code: In-Depth
The `.claude/` directory is the project's AI coding harness. It turns ad-hoc prompting into a repeatable delivery system.

### 1) Commands (`.claude/commands/`)
Command files are reusable workflows invoked as slash commands in Claude-enabled environments.

Current command set:
- `create-spec.md`
- `test-feature.md`
- `ship-feature.md`
- `code-review-feature.md`
- `seed-user.md`
- `seed-expense.md`

Typical lifecycle:
1. `/create-spec 09-delete-expense`
2. Implement against generated/updated spec
3. `/test-feature 09-delete-expense`
4. `/code-review-feature 09-delete-expense`
5. `/ship-feature`

This gives consistent planning, coding, testing, and shipping behavior.

### 2) Agents (`.claude/agents/`)
Agents are specialist instruction profiles for focused tasks:
- `spendly-test-writer.md`: creates/extends tests from specs
- `spendly-test-runner.md`: executes and analyzes tests
- `spendly-quality-reviewer.md`: code quality and maintainability checks
- `spendly-security-reviewer.md`: auth/input/data-handling security review

Why this matters:
- Improves review depth without context switching
- Standardizes what "done" means for feature quality
- Keeps security and tests first-class in each change

### 3) Skills (`.claude/skills/`)
Skills are deeper playbooks for domain-specific execution.

Current local skill:
- `frontend-design/SKILL.md`

Skill usage model:
- Load when task context matches the skill domain
- Follow skill conventions before free-form generation
- Reuse assets/patterns where possible for consistency

### 4) Specs (`.claude/specs/`)
Specs capture implementation slices and acceptance criteria.
The numbered spec chain (`01-...` to `09-...`) documents project evolution feature by feature.

Benefits:
- Traceable feature history
- Easier regression checks
- Better onboarding for contributors and AI agents

### 5) Hooks
There is currently no `.claude/hooks/` directory in this repo.
If introduced later, hooks should be documented with:
- Trigger condition
- Purpose
- Safety implications
- Fallback behavior on failure

### 6) Coding Harness Model
In this project, "coding harness" means the integrated system of:
- Instruction baseline (`CLAUDE.md`)
- Specs (`.claude/specs`)
- Workflow commands (`.claude/commands`)
- Specialist agents (`.claude/agents`)
- Domain skills (`.claude/skills`)

Together they create deterministic engineering flow instead of one-off prompting.

## CLAUDE.md as the Operating Contract
`CLAUDE.md` defines critical constraints for all contributors and agents, including:
- Flask/SQLite/vanilla-JS boundaries
- file ownership conventions (`app.py` routes, `database/db.py` DB logic)
- style and security expectations
- test execution patterns
- package change policy

If behavior in AI output drifts, update `CLAUDE.md` first.

## MCP, Plugins, and Tool Integrations
This project is designed to work well with MCP-enabled tools.

### GitHub MCP
Use for:
- PR creation and review workflows
- issue triage
- release operations
- CI signal inspection

### Figma MCP
Use for:
- extracting UI specs/content from design files
- converting design constraints into implementation tasks
- reducing mismatch between design and templates/CSS

### Railway Tooling / Plugin Workflow
Use for:
- project linking
- service deployment
- domain generation
- deployment status checks

Key deployment behavior for Spendly:
- `Procfile` runs Gunicorn:
  - `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
- `.railwayignore` avoids uploading local artifacts/tests/db files
- `requirements.txt` includes `gunicorn`

## Deployment Guide (Railway)
1. Authenticate Railway CLI
2. Link or initialize project
3. Deploy:
```bash
railway up --service spendly-flask --detach
```
4. Get domain:
```bash
railway domain --service spendly-flask
```
5. Verify health:
```bash
curl -I https://spendly-flask-production.up.railway.app
```

## Release Process
Current release tag pattern: `vX.Y.Z` (example: `v1.0.1`).

Recommended release flow:
1. Ensure tests pass
2. Ensure deployment is healthy
3. Tag release
4. Push tag
5. Publish release notes summarizing fixes and outcomes

## Security and Quality Notes
- Use parameterized SQL queries only
- Keep DB logic in `database/db.py`
- Do not commit secrets or local `.env` values
- Treat session/auth changes as security-sensitive
- Validate all user input server-side

## Contributing
1. Start from a spec (`.claude/specs`)
2. Keep changes small and testable
3. Run tests locally
4. Use command/agent workflow for review depth
5. Ship with explicit release notes
