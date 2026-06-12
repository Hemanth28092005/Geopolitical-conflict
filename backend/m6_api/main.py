import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.m6_api.routes import countries, trade_routes, hostility, simulation, forecast
from backend.m6_api.websocket.broadcaster import connect, disconnect, live_feed_loop
from backend.core.config import get_settings
from backend.core.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background WebSocket live feed
    task = asyncio.create_task(live_feed_loop())
    logger.info("FastAPI started — live feed running")
    yield
    task.cancel()
    logger.info("FastAPI shutting down")


app = FastAPI(
    title="Geopolitical Trade Intelligence API",
    description="Real-time trade risk and geopolitical conflict scoring for India",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(countries.router,    prefix="/api")
app.include_router(trade_routes.router, prefix="/api")
app.include_router(hostility.router,    prefix="/api")
app.include_router(simulation.router,   prefix="/api")
app.include_router(forecast.router,     prefix="/api")


@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "Geopolitical Trade Intelligence API",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.websocket("/ws/live-feed")
async def websocket_endpoint(websocket: WebSocket):
    await connect(websocket)
    try:
        # Send initial data on connect
        await websocket.send_json({"type": "connected", "message": "Live feed active"})
        while True:
            # Keep connection alive — listen for client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        disconnect(websocket)
