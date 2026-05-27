# RA Opportunity Monitor Agent

A small Python agent that scans an RA/research recruitment webpage, filters likely RA openings, deduplicates them with SQLite, and notifies you.

## Phase 1 MVP
- Scan 1 RA recruitment website
- Extract posts from links, card-style headings, and dynamic API feeds when available
- Keyword + simple relevance scoring (prioritizing AI/LLM-related openings)
- Save seen posts in SQLite with URL + content-hash deduplication
- Print or Gmail-notify new relevant openings

## Setup

```bash
cd ra-opportunity-agent-starter
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
RA_WEBSITE_URL=https://example.com/ra-recruitment-page
CHECK_INTERVAL_MINUTES=360
MIN_SCORE=2
USE_SYSTEM_PROXY=false
USE_LLM_CLASSIFIER=false
```

By default, scanner requests ignore system proxy settings. Set `USE_SYSTEM_PROXY=true` only if you intentionally need your Windows or shell proxy settings.

## Optional LLM classification

The default classifier uses local keyword scoring. To have an LLM determine whether each item is an RA opening, extract professor/group name, topic area, deadline, fit score, and explain the match, add:

```env
USE_LLM_CLASSIFIER=true
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

If LLM classification fails or is not configured, the agent falls back to the local keyword classifier.

Run one live Gemini classifier smoke test with a mock RA opening:

```bash
python -m tests.test_classifier_llm --live-llm --llm-results-file tests/llm_classifier_results.md -v
```

Run all live Gemini classifier tests:

```bash
python -m tests.test_classifier_llm --live-llm-all --llm-results-file tests/llm_classifier_results.md -v
```

Run once:

```bash
python -m src.main --once
```

Run continuously:

```bash
python -m src.main
```

## Optional Gmail notification

This uses Gmail SMTP with STARTTLS. Create a Gmail App Password and use that here, not your normal Gmail password.

```env
GMAIL_HOST=smtp.gmail.com
GMAIL_PORT=587
GMAIL_USER=yourgmail@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
GMAIL_TO=yourgmail@gmail.com
GMAIL_FROM=yourgmail@gmail.com
```

`GMAIL_FROM` is optional. If it is not set, the agent uses `GMAIL_USER` as the sender.

If Gmail is not configured, or if Gmail sending fails, notifications will print to console.

## Project structure

```text
ra_agent/
  main.py          # entry point and scheduler
  scanner.py       # webpage fetching + HTML parsing
  classifier.py    # keyword-based scoring for now
  db.py            # SQLite deduplication
  notifier.py      # console/Gmail notifications
  config.py        # env variables
```

## Next phases

Phase 2:
- Add LLM classifier for title + description relevance.

Phase 3:
- Add Outlook scanning through Microsoft Graph.

Phase 4:
- Add a small dashboard with FastAPI + Next.js.
