# EduTrack Backend

Transparent scholarship delivery platform backend.

## Quick Start

1. Copy env: `cp .env.example .env`
2. Start services: `docker compose up`
3. API docs: http://localhost:8000/docs
4. Health check: `curl http://localhost:8000/api/health`

## Environment Variables

See `.env.example` for all required variables with descriptions.

## Development

Install deps: `pip install -r requirements.txt`
Run locally: `uvicorn app.main:app --reload`
