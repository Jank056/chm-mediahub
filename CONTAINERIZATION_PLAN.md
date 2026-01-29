# CHM Server Containerization Plan

## Current State (EC2: 13.220.20.135)

### Running Services

| Service | Port | Type | Dependencies |
|---------|------|------|--------------|
| MediaHub Backend | 8002 | Docker | PostgreSQL, Redis, Report Automation |
| MediaHub Frontend | 3002 | Docker | Backend API |
| Chatbot Backend | 8000 | Bare Metal | ChromaDB, OpenAI API |
| Chatbot Frontend | 3000 | Bare Metal | Backend API |
| PostgreSQL | 5432 | Docker | - |
| Redis | 6379 | Docker | - |

### Problems with Current Setup

1. **Dependency Conflicts**: Chatbot and other Python services share system Python
2. **No Isolation**: A bad install can break multiple services
3. **Hard to Reproduce**: New deployments require manual setup
4. **No Easy Rollback**: Can't easily revert to previous versions
5. **Memory/Resource Competition**: Services compete for resources

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Stack                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Shared Infrastructure                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │   Postgres   │  │    Redis     │  │      Nginx       │   │   │
│  │  │    :5432     │  │    :6379     │  │   :80 / :443     │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       MediaHub Stack                          │  │
│  │  ┌────────────────────┐      ┌────────────────────────────┐  │  │
│  │  │   mediahub-front   │      │      mediahub-back         │  │  │
│  │  │      :3002         │─────▶│         :8002              │  │  │
│  │  │   (Next.js 15)     │      │   (FastAPI + Report Gen)   │  │  │
│  │  └────────────────────┘      └────────────────────────────┘  │  │
│  │                                      │                        │  │
│  │                                      ▼                        │  │
│  │                              /home/ubuntu/                    │  │
│  │                              chm_report_automation            │  │
│  │                              (volume mount)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       Chatbot Stack                           │  │
│  │  ┌────────────────────┐      ┌────────────────────────────┐  │  │
│  │  │   chatbot-front    │      │      chatbot-back          │  │  │
│  │  │      :3000         │─────▶│         :8000              │  │  │
│  │  │   (Next.js 16)     │      │   (FastAPI + ChromaDB)     │  │  │
│  │  └────────────────────┘      └────────────────────────────┘  │  │
│  │                                      │                        │  │
│  │                                      ▼                        │  │
│  │                              /data/chroma_db                  │  │
│  │                              /data/pdfs                       │  │
│  │                              (volume mounts)                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Chatbot Containerization

#### 1.1 Create Chatbot Backend Dockerfile

```dockerfile
# chm-chatbot/Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# System dependencies for ChromaDB and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Create data directories
RUN mkdir -p /data/chroma_db /data/pdfs /data/transcripts

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.2 Create Chatbot Frontend Dockerfile

```dockerfile
# chm-chatbot/chm-chatbot-frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

#### 1.3 Add to docker-compose.yml

```yaml
# Add to existing docker-compose.prod.yml

  chatbot-backend:
    build:
      context: ../chm-chatbot
      dockerfile: Dockerfile.backend
    container_name: chatbot-backend
    restart: unless-stopped
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      CHROMA_PERSIST_DIRECTORY: /data/chroma_db
    volumes:
      - chatbot_chroma:/data/chroma_db
      - chatbot_pdfs:/data/pdfs
      - chatbot_transcripts:/data/transcripts
    networks:
      - mediahub
    ports:
      - "8000:8000"

  chatbot-frontend:
    build:
      context: ../chm-chatbot/chm-chatbot-frontend
      dockerfile: Dockerfile
    container_name: chatbot-frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - chatbot-backend
    networks:
      - mediahub
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  chatbot_chroma:
  chatbot_pdfs:
  chatbot_transcripts:
```

### Phase 2: Add Nginx Reverse Proxy

#### 2.1 Create nginx.conf

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream mediahub_frontend {
        server mediahub-frontend:3000;
    }

    upstream mediahub_backend {
        server mediahub-backend:8000;
    }

    upstream chatbot_frontend {
        server chatbot-frontend:3000;
    }

    upstream chatbot_backend {
        server chatbot-backend:8000;
    }

    # MediaHub Portal
    server {
        listen 80;
        server_name mediahub.chmedia.com;  # Replace with actual domain

        location / {
            proxy_pass http://mediahub_frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        location /api/ {
            proxy_pass http://mediahub_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # Chatbot
    server {
        listen 80;
        server_name chatbot.chmedia.com;  # Replace with actual domain

        location / {
            proxy_pass http://chatbot_frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
        }

        location /api/ {
            proxy_pass http://chatbot_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

#### 2.2 Add Nginx to docker-compose

```yaml
  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: unless-stopped
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - mediahub-frontend
      - mediahub-backend
      - chatbot-frontend
      - chatbot-backend
    networks:
      - mediahub
```

### Phase 3: Data Migration

#### 3.1 Migrate ChromaDB Data

```bash
# Backup existing data
ssh ubuntu@13.220.20.135 "tar -czvf chroma_backup.tar.gz ~/chm-chatbot/chroma_db"

# Create Docker volume and restore
docker volume create chatbot_chroma
docker run --rm -v chatbot_chroma:/data -v ~/chroma_backup.tar.gz:/backup.tar.gz alpine \
    tar -xzvf /backup.tar.gz -C /data
```

#### 3.2 Migrate PDF Library

```bash
# Similar process for PDFs and transcripts
docker volume create chatbot_pdfs
docker volume create chatbot_transcripts
```

### Phase 4: Cleanup

1. Stop bare metal services
2. Remove old venv directories
3. Update DNS/firewall if needed
4. Test all endpoints

---

## Benefits After Containerization

| Aspect | Before | After |
|--------|--------|-------|
| Deployment | Manual pip install | `docker compose up -d` |
| Isolation | Shared Python | Isolated containers |
| Rollback | Difficult | `docker compose down && docker compose up -d` with old tag |
| Monitoring | Manual | `docker stats`, `docker logs` |
| Updates | Risky | Pull new image, restart |
| Resource Limits | None | Can set CPU/memory limits |

---

## Timeline Estimate

| Phase | Tasks | Duration |
|-------|-------|----------|
| Phase 1 | Chatbot Dockerfiles + test | 2-3 hours |
| Phase 2 | Nginx reverse proxy | 1 hour |
| Phase 3 | Data migration | 30 min |
| Phase 4 | Testing + cleanup | 1 hour |
| **Total** | | **4-5 hours** |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ChromaDB data loss | Full backup before migration |
| API downtime | Blue-green deployment possible |
| Memory pressure | Set container limits |
| Port conflicts | Use Nginx to route all traffic |

---

## Next Steps

1. [ ] Create backup of all data
2. [ ] Write chatbot Dockerfiles
3. [ ] Test locally with docker compose
4. [ ] Deploy to EC2
5. [ ] Verify all services
6. [ ] Stop bare metal services
7. [ ] Clean up old files
