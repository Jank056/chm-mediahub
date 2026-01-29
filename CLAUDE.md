# CHM MediaHub - Claude Code Context

Client-facing analytics portal for Community Health Media. This is a standalone, deployable application.

## Quick Start

```bash
# Local development
docker compose up -d

# Or without Docker
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8001
cd frontend && npm install && npm run dev
```

## System Overview

**CHM MediaHub** provides clients with:
1. **Analytics Dashboard** - View counts and engagement across YouTube, LinkedIn, X
2. **Medical Chatbot** - Search CHM podcast content with citations
3. **Report Generator** - Upload transcript + survey → download branded PPTX

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CHM MediaHub                            │
├─────────────────────────────────────────────────────────────┤
│   Frontend (Next.js)     │     Backend (FastAPI)            │
│   - Dashboard            │     - Auth/Users                 │
│   - Analytics views      │     - Webhook receiver           │
│   - Chatbot UI           │     - Analytics API              │
│   - Report generator     │     - Report jobs                │
├─────────────────────────────────────────────────────────────┤
│   PostgreSQL             │     Redis (sessions)             │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ Webhook (optional)
         │ POST /webhook/sync
         │
    External data source
```

### Ports

| Service | Port |
|---------|------|
| Frontend | 3001 |
| Backend | 8001 |
| PostgreSQL | 5432 |

---

## Data Model

**Hierarchy**: Client → Project → KOL Group → Shoot → Clip → Post

```
Client (e.g., "Pfizer")
  └── Project (e.g., "Oncology Campaign 2026")
       └── KOL Group (e.g., "Dr. Smith Series")
            └── Shoot (recording session)
                 └── Clip (edited video)
                      └── Post (published to platform)
```

---

## Core Rules (Always Apply)

### Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Never commit: `.env`, credentials, `node_modules`, `venv`

### Code Style
- Python: Type hints, async/await, Pydantic models
- TypeScript: Strict types, no `any`

### Scope Discipline
- Minimal changes only
- Don't add unrequested features
- Don't refactor outside scope

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app entry point |
| `backend/models/` | SQLAlchemy models |
| `backend/routers/` | API route handlers |
| `backend/services/` | Business logic |
| `frontend/src/app/` | Next.js pages |
| `docs/WEBHOOK_API.md` | Webhook contract documentation |

---

## Database

```bash
# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
cd backend && alembic upgrade head
```

---

## Development Without External Data

MediaHub is **self-contained**. For local development:

```bash
# Seed sample data
python backend/scripts/seed_data.py
```

This creates mock clips, posts, and shoots for testing the UI.

---

## Webhook Integration

MediaHub receives data updates via webhook. See `docs/WEBHOOK_API.md` for the full API contract.

**Endpoint**: `POST /webhook/sync`
**Auth**: `X-API-Key` header

Any authorized system can push data - the webhook is documented, not implementation-specific.

---

## Deployment

**Target**: EC2 at `chmbot.communityhealth.media`

```bash
# Deploy to production
./deploy.sh
```

---

## Implementation Plan

See `IMPLEMENTATION_PLAN.md` for the full PRD and phase breakdown.

**Current Phase**: Foundation (auth, user management, basic UI)
