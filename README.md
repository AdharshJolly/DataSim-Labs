# DataSim Lab

Synthetic Dataset Generation Platform scaffold.

## Stack

- Frontend: Next.js + TypeScript + TailwindCSS + ShadCN UI + TanStack Table
- Backend: FastAPI + Pydantic
- Data engine: pandas + numpy + faker
- Storage: PostgreSQL + Redis
- Deployment: local development first (Docker can be added later)

## Run (initial scaffold)

1. Copy `.env.example` to `.env` and keep the Supabase `DATABASE_URL`.
2. Start backend:
   - `cd backend`
   - `venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
   - `alembic upgrade head`
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
3. Start frontend in a second terminal:
   - `cd frontend`
   - `npm install`
   - `npm run dev`
4. Open:
   - Frontend: `http://localhost:3000`
   - Backend docs: `http://localhost:8000/docs`
