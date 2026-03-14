# DataSim Lab

Synthetic Dataset Generation Platform scaffold.

## Stack

- Frontend: Next.js + TypeScript + TailwindCSS + ShadCN UI + TanStack Table
- Backend: FastAPI + Pydantic
- Data engine: pandas + numpy + faker
- Storage: PostgreSQL
- Deployment: local development first (Docker can be added later)

## Run (initial scaffold)

1. Copy `.env.example` to `.env` and set your own `DATABASE_URL` and `JWT_SECRET_KEY`.
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

## API Flow

Authentication:

1. Register user:
   - `POST /api/v1/auth/register`
2. Login:
   - `POST /api/v1/auth/login`
3. Current user:
   - `GET /api/v1/auth/me`

Dataset ownership and versioning:

1. Create dataset:
   - `POST /api/v1/dataset/create`
2. Save attributes:
   - `POST /api/v1/dataset/attributes`
3. Preview 10 rows:
   - `POST /api/v1/dataset/preview`
4. Generate dataset files:
   - `POST /api/v1/dataset/generate`
5. List/download files:
   - `GET /api/v1/dataset/download/{dataset_id}`
6. List user datasets:
   - `GET /api/v1/dataset/list`
7. Dataset detail:
   - `GET /api/v1/dataset/{dataset_id}`
8. Dataset versions:
   - `GET /api/v1/dataset/{dataset_id}/versions`

## Example Requests

Create dataset:

```json
{
  "name": "customer_synthetic",
  "description": "Synthetic customer profile dataset"
}
```

Register request:

```json
{
  "email": "researcher@example.com",
  "password": "strong-password-123"
}
```

Login request:

```json
{
  "email": "researcher@example.com",
  "password": "strong-password-123"
}
```

Save attributes:

```json
{
  "dataset_id": "<dataset_id>",
  "attributes": [
    {
      "name": "age",
      "type": "integer",
      "description": "Customer age",
      "constraints": { "min": 18, "max": 70 },
      "distribution": "normal",
      "null_percentage": 5
    },
    {
      "name": "email",
      "type": "email",
      "description": "Customer email",
      "constraints": {},
      "distribution": "uniform",
      "null_percentage": 0
    }
  ]
}
```

Preview request:

```json
{
  "dataset_version_id": "<dataset_version_id>"
}
```

Generation request:

```json
{
  "dataset_id": "<dataset_id>",
  "row_count": 100000,
  "formats": ["csv", "json", "excel"]
}
```
