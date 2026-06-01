# Job Copilot

A personal job application tracker with auto-fill from job postings, status tracking, and a stats dashboard.

**Live demo:** https://job-copilot-frontend.onrender.com

![CI](https://github.com/Xing312/job-copilot/actions/workflows/ci.yml/badge.svg)

## Features

- **Auto-fill** — paste a job URL or raw JD text; the app extracts title, company, location, salary, and work type automatically
- **LLM extraction** — optional Groq (llama-3.3-70b) pass improves accuracy; falls back to regex + custom spaCy NER when unavailable
- **Extraction pipeline** — JSON-LD structured data → Jina Reader → LLM → spaCy NER (cascading fallbacks)
- **Application tracking** — add, edit, delete applications; update status with one click
- **Dashboard** — status breakdown, weekly application trend, platform and work-type distribution (Recharts)
- **API key auth** — simple header-based protection for personal deployments

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy, Python 3.12 |
| NLP | spaCy 3 (custom NER) + Groq LLM (optional) |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose, GitHub Actions, Render |

## Local Development

**Prerequisites:** Docker Desktop

```bash
# Clone and start
git clone https://github.com/Xing312/job-copilot.git
cd job-copilot
make start

# App is running at:
#   Frontend  →  http://localhost:5173
#   Backend   →  http://localhost:8000
```

### Common commands

```bash
make start      # start all services in background
make stop       # stop all services
make restart    # restart backend (after Python changes)
make logs       # tail backend logs
make test       # run pytest suite inside the backend container
make train      # retrain the custom spaCy NER model
```

### Environment variables

Copy `.env.example` to `.env` to customise database credentials. API key auth is **disabled by default** in local dev (set `API_KEY` to enable).

To enable LLM-based extraction, add your Groq API key (free tier at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=gsk_...
```

If `GROQ_API_KEY` is empty, the pipeline silently skips the LLM step and uses regex + spaCy.

## Deployment (Render)

This repo includes a `render.yaml` Blueprint for one-click deployment.

1. Fork / push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint** → select this repo
3. Render creates the backend, frontend, and PostgreSQL database automatically
4. After the first deploy, set these env vars in the Render dashboard:

| Service | Variable | Value |
|---------|----------|-------|
| backend | `FRONTEND_URL` | `https://job-copilot-frontend.onrender.com` |
| backend | `GROQ_API_KEY` | *(optional — get a free key at console.groq.com)* |
| frontend | `VITE_API_URL` | `https://job-copilot-backend.onrender.com` |
| frontend | `VITE_API_KEY` | *(copy the auto-generated `API_KEY` from backend)* |

5. Trigger a manual redeploy on both services after setting the vars

> **Note:** Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

## Project Structure

```
├── backend/
│   ├── api/            # FastAPI routers (applications, extract, stats, auth)
│   ├── db/             # SQLAlchemy engine and session
│   ├── models/         # ORM models
│   ├── services/       # extractor.py (regex/NER), llm_extractor.py (Groq)
│   └── tests/          # pytest suite (SQLite in-memory)
├── corpus/
│   ├── annotations.json        # NER training data (107 examples)
│   ├── job_copilot_ner/        # Trained spaCy model
│   └── train.py                # Training script
├── frontend/
│   └── src/
│       ├── api/        # fetch wrappers
│       ├── components/ # NavBar
│       └── pages/      # Applications, AddApplication, ApplicationDetail, Dashboard
├── scripts/            # Corpus-building utilities
├── docker-compose.yml
├── render.yaml
└── Makefile
```

## NER Model

The custom NER model is fine-tuned from `en_core_web_sm` to recognise `JOB_TITLE` (F=0.81) and `COMPANY` (F=0.28) entities in job posting text. It acts as a fallback when structured extraction (JSON-LD / title-line regex / LLM) does not find a value.

To retrain after adding annotations to `corpus/annotations.json`:

```bash
make train
make restart
```

## License

MIT © [Xing312](https://github.com/Xing312)
