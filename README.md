# WarImpactForecast

## Local development

From the project root, start PostgreSQL and Redis:

```powershell
docker compose up -d
```

Install backend dependencies and start FastAPI:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.m6_api.main:app --reload --port 8000
```

In another terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/ws` to FastAPI on
port `8000`.

For a separately hosted frontend, copy `frontend/.env.example` to
`frontend/.env` and set `VITE_API_BASE_URL` and `VITE_WS_URL` to the public
backend URLs. Add the frontend origin to `CORS_ORIGINS` in the root `.env`.
