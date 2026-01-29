# CHM MediaHub - Implementation Plan

## Product Summary

**CHM MediaHub** is a unified client portal that gives Community Health Media access to:
1. **Analytics Dashboard** - View counts and engagement metrics across YouTube, LinkedIn, X
2. **Medical Chatbot** - Search across CHM podcast content with citations
3. **Webinar Report Generator** - Upload transcript + survey → download branded PPTX

**Not included (intentionally):**
- Video clipping/editing tools
- Face tracking
- n8n workflow access
- Posting/scheduling capabilities (you manage this)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CHM MediaHub                                │
│                   (Client-Facing Portal)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │   Analytics  │  │   Chatbot    │  │  Report Generator    │  │
│   │   Dashboard  │  │   Search     │  │  (Upload → PPTX)     │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │              │
├──────────┴─────────────────┴──────────────────────┴──────────────┤
│                     Portal Backend (FastAPI)                     │
│              Auth │ Users │ Jobs │ API Gateway                   │
├──────────────────────────────────────────────────────────────────┤
│   PostgreSQL     │    Redis      │    File Storage              │
│   (users/auth)   │   (sessions)  │   (reports)                  │
└─────────┬────────────────┬───────────────────┬───────────────────┘
          │                │                   │
          ▼                ▼                   ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐
   │ Ops-Console │  │  Chatbot    │  │ Report Pipeline │
   │    API      │  │    API      │  │   (Python)      │
   │ (analytics) │  │  (search)   │  │                 │
   └─────────────┘  └─────────────┘  └─────────────────┘
        YOUR            EXISTING         EXISTING
      MACHINE           EC2              LOCAL
```

---

## Deployment Target

**Single EC2 Instance** (existing: 13.220.20.135)

| Service | Port | Status |
|---------|------|--------|
| Chatbot Backend | 8000 | ✅ Running |
| Chatbot Frontend | 3000 | ✅ Running |
| MediaHub Backend | 8001 | 🆕 New |
| MediaHub Frontend | 3001 | 🆕 New |
| PostgreSQL | 5432 | 🆕 New (local) |
| Redis | 6379 | 🆕 New (local) |

**No additional AWS cost** - runs on existing t3.medium

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js 15 + React 19 + Tailwind | Consistent with existing work |
| Backend | FastAPI + Python 3.11 | Consistent with chatbot/reports |
| Database | PostgreSQL 16 | Users, sessions, job history |
| Cache | Redis 7 | Session tokens, rate limiting |
| Auth | JWT + bcrypt | Simple, stateless |
| File Storage | Local disk | Reports stored on EC2 |

---

## Feature Breakdown

### 1. Authentication & User Management

**Capabilities:**
- Email/password login
- JWT tokens (access + refresh)
- Email invitation system
- Role-based access (Admin, Editor, Viewer)
- User management dashboard (invite, list, revoke)

**Database Schema:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',  -- admin, editor, viewer
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    revoked BOOLEAN DEFAULT false
);

CREATE TABLE invitations (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    invited_by UUID REFERENCES users(id),
    token VARCHAR(255) UNIQUE,
    role VARCHAR(50) DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    accepted_at TIMESTAMP
);
```

**API Endpoints:**
```
POST /auth/login          - Email + password → JWT tokens
POST /auth/logout         - Revoke session
POST /auth/refresh        - Refresh access token
POST /auth/invite         - Send email invitation (admin only)
POST /auth/accept-invite  - Accept invitation, set password
GET  /users               - List users (admin only)
PUT  /users/{id}          - Update user role/status (admin only)
DELETE /users/{id}        - Deactivate user (admin only)
```

### 2. Analytics Dashboard

**Capabilities:**
- Platform metrics (YouTube, LinkedIn, X)
- View counts, likes, comments
- 7-day and 30-day views
- Per-channel breakdown
- Refresh on demand

**Data Source:** Ops-Console API (your machine)

**Implementation Options:**

*Option A: Direct API Proxy*
- MediaHub backend proxies requests to Ops-Console
- Requires Ops-Console to be accessible from EC2
- Real-time data

*Option B: Cached/Synced Data*
- You manually export or sync analytics periodically
- MediaHub serves from local database
- Stale but simpler

**Recommended:** Option A with caching
- Cache analytics for 1 hour
- Background job refreshes data
- Fallback to cache if Ops-Console unavailable

**API Endpoints:**
```
GET /analytics/overview      - Summary stats across platforms
GET /analytics/youtube       - YouTube channel metrics
GET /analytics/linkedin      - LinkedIn org metrics
GET /analytics/x             - X account metrics
GET /analytics/posts         - Recent posts with engagement
POST /analytics/refresh      - Force refresh (admin only)
```

**Note:** You'll need to expose Ops-Console API or set up a sync mechanism.

### 3. Chatbot Integration

**Capabilities:**
- Embedded chatbot UI (or link to standalone)
- Search across CHM podcast content
- Citations with YouTube timestamps
- PDF document library
- Conversation history

**Data Source:** Existing Chatbot API (13.220.20.135:8000)

**Implementation:**
- Proxy requests through MediaHub backend (adds auth layer)
- Or: Direct frontend calls to chatbot API (simpler)

**API Endpoints:**
```
POST /chat/query         - Proxy to chatbot /query
GET  /chat/pdfs          - Proxy to chatbot /pdfs
GET  /chat/health        - Proxy to chatbot /health
```

### 4. Report Generator

**Capabilities:**
- Upload transcript (DOCX) + survey (CSV)
- Configure report metadata (event name, date, speakers)
- Generate branded PPTX
- Download completed reports
- View report history

**Data Source:** Report Automation pipeline (local Python)

**Implementation:**
- File upload to server
- Background job runs `run_pipeline()`
- Job status polling
- Download when complete

**Database Schema:**
```sql
CREATE TABLE report_jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    config JSONB,  -- event name, date, speakers, etc.
    transcript_path VARCHAR(500),
    survey_path VARCHAR(500),
    output_path VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**API Endpoints:**
```
POST /reports/create      - Upload files + config, start job
GET  /reports             - List user's reports
GET  /reports/{id}        - Get job status
GET  /reports/{id}/download - Download completed PPTX
DELETE /reports/{id}      - Delete report (admin or owner)
```

---

## Frontend Pages

| Route | Page | Access |
|-------|------|--------|
| `/` | Dashboard (analytics overview) | All |
| `/login` | Login form | Public |
| `/invite/:token` | Accept invitation | Public |
| `/analytics` | Detailed analytics | All |
| `/chat` | Chatbot interface | All |
| `/reports` | Report list + generator | Editor+ |
| `/reports/new` | Create new report | Editor+ |
| `/reports/:id` | Report status/download | Owner |
| `/users` | User management | Admin |
| `/settings` | Account settings | All |

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)
- [ ] Create project structure (`chm_mediahub/`)
- [ ] Set up FastAPI backend scaffold
- [ ] Set up Next.js frontend scaffold
- [ ] PostgreSQL schema + migrations
- [ ] User model + auth endpoints
- [ ] JWT token handling
- [ ] Login/logout UI

### Phase 2: User Management (Days 4-5)
- [ ] Email invitation system
- [ ] Accept invitation flow
- [ ] User list page (admin)
- [ ] Role-based route protection
- [ ] Session management

### Phase 3: Analytics Dashboard (Days 6-8)
- [ ] Design analytics data models
- [ ] Ops-Console API integration (or mock data)
- [ ] Analytics API endpoints
- [ ] Dashboard UI components
- [ ] Platform cards (YouTube, LinkedIn, X)
- [ ] Caching layer

### Phase 4: Chatbot Integration (Days 9-10)
- [ ] Chatbot API proxy endpoints
- [ ] Chat UI component
- [ ] PDF library browser
- [ ] Integrate into MediaHub layout

### Phase 5: Report Generator (Days 11-14)
- [ ] File upload endpoints
- [ ] Background job system (simple queue)
- [ ] Integrate report automation pipeline
- [ ] Job status polling
- [ ] Report list UI
- [ ] Report creation form
- [ ] Download functionality

### Phase 6: Polish & Deploy (Days 15-17)
- [ ] Error handling + loading states
- [ ] Mobile responsiveness
- [ ] Install PostgreSQL + Redis on EC2
- [ ] Deploy backend + frontend
- [ ] Configure Nginx routing
- [ ] Test all features
- [ ] Create admin user

---

## File Structure

```
chm_mediahub/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (env vars)
│   ├── database.py             # SQLAlchemy setup
│   ├── models/
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── invitation.py
│   │   └── report_job.py
│   ├── routers/
│   │   ├── auth.py             # Login, logout, invite
│   │   ├── users.py            # User management
│   │   ├── analytics.py        # Analytics proxy/cache
│   │   ├── chat.py             # Chatbot proxy
│   │   └── reports.py          # Report generation
│   ├── services/
│   │   ├── auth_service.py     # JWT, password hashing
│   │   ├── email_service.py    # Send invitations
│   │   ├── analytics_service.py
│   │   └── report_service.py   # Run pipeline
│   ├── middleware/
│   │   └── auth_middleware.py  # JWT verification
│   ├── migrations/
│   │   └── ...                 # Alembic migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Dashboard
│   │   │   ├── layout.tsx      # Root layout
│   │   │   ├── login/
│   │   │   ├── analytics/
│   │   │   ├── chat/
│   │   │   ├── reports/
│   │   │   └── users/
│   │   ├── components/
│   │   │   ├── ui/             # Buttons, cards, etc.
│   │   │   ├── analytics/      # Analytics widgets
│   │   │   ├── chat/           # Chat components
│   │   │   └── reports/        # Report components
│   │   ├── lib/
│   │   │   ├── api.ts          # API client
│   │   │   ├── auth.ts         # Auth helpers
│   │   │   └── utils.ts
│   │   └── stores/
│   │       └── auth-store.ts   # Zustand auth state
│   ├── package.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── .env.example
└── README.md
```

---

## Environment Variables

```env
# Backend
DATABASE_URL=postgresql://mediahub:password@localhost:5432/mediahub
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# External Services
CHATBOT_API_URL=http://localhost:8000
OPS_CONSOLE_API_URL=http://your-machine:8015  # Or mock

# Email (for invitations)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
FROM_EMAIL=noreply@chm-mediahub.com

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

## Analytics Data Challenge

**Problem:** Ops-Console runs on your local machine, not accessible from EC2.

**Solutions:**

1. **Manual Sync** (Simplest for MVP)
   - Export analytics JSON weekly
   - Upload to EC2 or paste into database
   - Dashboard shows "Last updated: X"

2. **Scheduled Push** (Better)
   - Cron job on your machine pushes data to EC2
   - `curl -X POST https://mediahub/api/analytics/sync -d @data.json`

3. **VPN/Tunnel** (Most Complex)
   - Set up secure tunnel between your machine and EC2
   - Direct API calls work

**Recommendation for MVP:** Start with mock data, then implement #2.

---

## Security Considerations

- [ ] HTTPS only (via Nginx + Let's Encrypt)
- [ ] Password hashing with bcrypt
- [ ] JWT tokens with short expiry
- [ ] Rate limiting on auth endpoints
- [ ] Input validation (Pydantic)
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] CORS configured for frontend origin only
- [ ] Secure file upload (validate types, size limits)

---

## Demo Checklist

Before showing to CHM:

- [ ] Login works with test accounts
- [ ] Dashboard shows analytics (mock or real)
- [ ] Chatbot search returns results
- [ ] Report generator completes a sample report
- [ ] User invitation flow works
- [ ] Mobile view is usable
- [ ] No console errors
- [ ] Loading states for all async operations

---

## Cost Summary

| Item | Cost |
|------|------|
| EC2 (existing t3.medium) | $0 additional |
| Domain (optional for demo) | $0 (use IP) |
| SSL (optional for demo) | $0 |
| Email sending (low volume) | $0 (Gmail SMTP) |
| **Total for MVP** | **$0 additional** |

---

## Next Steps

1. **Create project directory structure**
2. **Set up backend with auth endpoints**
3. **Set up frontend with login page**
4. **Test auth flow locally**
5. **Add analytics (mock data first)**
6. **Add chatbot integration**
7. **Add report generator**
8. **Deploy to EC2**
9. **Demo to CHM**
