# Contributing Guide

Thanks for your interest in contributing to DataSim-Labs.

## Development Workflow

1. Fork the repository and create a feature branch from `development`.
2. Keep pull requests focused and small.
3. Follow existing code style and architecture patterns.
4. Ensure frontend build and backend syntax checks pass before opening a PR.

## Local Setup

1. Backend:
   - `cd backend`
   - `venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
   - `python run_services.py`
2. Frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## Commit Style

Use conventional prefixes when possible:

- `feat:` new feature
- `fix:` bug fix
- `refactor:` internal improvement
- `docs:` documentation changes

## Pull Requests

Please include:

- What changed
- Why it changed
- How it was tested
- Any migration or environment updates

## Security

Do not commit secrets, API keys, or `.env` files. Report security issues privately (see `SECURITY.md`).
