.PHONY: db-up db-down backend frontend install create-admin

# Start PostgreSQL and Redis
db-up:
	docker compose up -d

# Stop PostgreSQL and Redis
db-down:
	docker compose down

# Install backend dependencies
install-backend:
	cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt

# Install frontend dependencies
install-frontend:
	cd frontend && npm install

# Install all dependencies
install: install-backend install-frontend

# Run backend (port 8002)
backend:
	cd backend && uvicorn main:app --reload --port 8002

# Run frontend (port 3002)
frontend:
	cd frontend && npm run dev -- -p 3002

# Create admin user
create-admin:
	cd backend && python3 scripts/create_admin.py $(EMAIL) $(PASSWORD)

# Example: make create-admin EMAIL=admin@chm.com PASSWORD=secretpassword
