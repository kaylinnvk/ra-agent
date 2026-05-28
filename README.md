# RA Opportunity Monitor Agent

A small Python agent that scans an RA/research recruitment webpage, filters likely AI/ML-related RA openings, deduplicates posts by normalized URL plus content hash, and notifies you by Gmail.

Outlook/Microsoft Graph scanning is intentionally skipped for now.

## Features

- Scan one RA recruitment website
- Extract posts from links, card-style headings, JSON data, and simple dynamic API feeds
- Keyword classifier with optional Gemini relevance filtering
- Persistent deduplication with SQLite locally or Postgres/Supabase in production
- Gmail SMTP notification for new relevant openings
- Run/source/finding logs for deployed runs

## Setup

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` for local development:

```env
RA_WEBSITE_URL=https://example.com/ra-recruitment-page
CHECK_INTERVAL_MINUTES=360
MIN_SCORE=2

DB_BACKEND=sqlite
SQLITE_PATH=data/ra_agent.sqlite
```

Run once:

```bash
python -m src.main --once
```

Run continuously on your machine:

```bash
python -m src.main
```

## Database

The agent uses SQLite unless `DB_BACKEND=postgres` and `DATABASE_URL` is set. GitHub Actions should use Postgres because files created during scheduled workflow runs are not persistent.

Required database env vars:

```env
DB_BACKEND=sqlite
SQLITE_PATH=data/ra_agent.sqlite
DATABASE_URL=
```

For production:

```env
DB_BACKEND=postgres
DATABASE_URL=postgresql://...
```

The agent creates these tables automatically:

- `seen_posts`
- `agent_runs`
- `source_logs`
- `findings`

## Supabase Postgres

1. Create a Supabase project at `https://supabase.com`.
2. Open Project Settings, then Database.
3. Copy the connection string for the transaction/session pooler or direct database connection.
4. Replace the password placeholder with your database password.
5. Use that value as `DATABASE_URL` in GitHub Actions Secrets.

Supabase URLs usually look like:

```text
postgresql://postgres.your-project:password@aws-...pooler.supabase.com:6543/postgres
```

## GitHub Actions Deployment

The workflow lives at `.github/workflows/ra-agent.yml`. It runs every 45 minutes and can also be started manually.

Add these GitHub repository secrets in Settings, Secrets and variables, Actions:

```text
DATABASE_URL
RA_WEBSITE_URL
MIN_SCORE
USE_LLM_CLASSIFIER
GEMINI_API_KEY
GEMINI_MODEL
GEMINI_BASE_URL
GMAIL_HOST
GMAIL_PORT
GMAIL_USER
GMAIL_APP_PASSWORD
GMAIL_TO
GMAIL_FROM
```

Recommended values:

```text
MIN_SCORE=2
USE_LLM_CLASSIFIER=true
GEMINI_MODEL=gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GMAIL_HOST=smtp.gmail.com
GMAIL_PORT=587
```

`GMAIL_FROM` is optional. If it is empty, the agent uses `GMAIL_USER`.

To manually trigger the workflow, open GitHub Actions, choose `RA Agent`, then select `Run workflow`.

## Gmail Notification

This uses Gmail SMTP with STARTTLS. Create a Gmail App Password and use that here, not your normal Gmail password.

```env
GMAIL_HOST=smtp.gmail.com
GMAIL_PORT=587
GMAIL_USER=yourgmail@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
GMAIL_TO=yourgmail@gmail.com
GMAIL_FROM=yourgmail@gmail.com
```

If Gmail is not configured, or if Gmail sending fails, notifications print to the console.

## Optional Gemini Filtering

The default classifier uses local keyword scoring. To have Gemini classify each item, extract professor/group name, topic area, deadline, fit score, and explain the match, add:

```env
USE_LLM_CLASSIFIER=true
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

If Gemini fails or is not configured, the agent falls back to the local keyword classifier.

## Deployment Checks

Test the configured database:

```bash
python -m src.main --check-db
```

Send a Gmail smoke-test email:

```bash
python -m src.main --test-gmail
```

Run one scan without writing findings or sending notifications:

```bash
python -m src.main --dry-run
```

## Tests

Compile the main modules:

```bash
python -m py_compile src/config.py src/notifier.py src/main.py
```

Run existing tests:

```bash
python -m unittest
```

Live Gemini tests are opt-in because they call the API:

```bash
python -m tests.test_classifier_llm --live-llm --llm-results-file tests/llm_classifier_results.md -v
```

## Project Structure

```text
src/
  main.py        # entry point, scheduler, run logging
  scanner.py     # webpage fetching + parsing
  classifier.py  # keyword and Gemini relevance classification
  db.py          # SQLite/Postgres persistence and deduplication
  notifier.py    # console/Gmail notifications
  config.py      # env variables
```
