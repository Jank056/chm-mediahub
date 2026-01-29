#!/bin/bash
set -e

echo "=== CHM MediaHub Deployment ==="

# Check for .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.production.example to .env and fill in your values"
    exit 1
fi

# Load environment
source .env

# Validate required vars
if [ "$JWT_SECRET" = "CHANGE_THIS_GENERATE_NEW_SECRET" ] || [ -z "$JWT_SECRET" ]; then
    echo "ERROR: JWT_SECRET not set! Generate with: openssl rand -hex 64"
    exit 1
fi

if [ "$WEBHOOK_API_KEY" = "CHANGE_THIS_MUST_MATCH_OPS_CONSOLE" ] || [ -z "$WEBHOOK_API_KEY" ]; then
    echo "ERROR: WEBHOOK_API_KEY not set! Generate with: openssl rand -hex 32"
    exit 1
fi

echo "Building and starting services..."
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "=== Health Check ==="
curl -s http://localhost:8002/health || echo "Backend not responding yet..."

echo ""
echo ""
echo "=== Deployment Complete ==="
echo "Backend:  http://localhost:8002"
echo "Frontend: http://localhost:3002"
echo ""
echo "To create admin user:"
echo "  docker exec -it mediahub-backend python scripts/create_admin.py"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
