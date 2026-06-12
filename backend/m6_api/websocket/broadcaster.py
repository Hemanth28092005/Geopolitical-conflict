import asyncio
import json
from datetime import datetime, timezone
from fastapi import WebSocket
from backend.core.logger import logger

# Store all active connections
active_connections: list[WebSocket] = []


async def connect(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WS client connected — total: {len(active_connections)}")


def disconnect(websocket: WebSocket):
    if websocket in active_connections:
        active_connections.remove(websocket)
    logger.info(f"WS client disconnected — total: {len(active_connections)}")


async def broadcast(message: dict):
    """Send message to all connected WebSocket clients."""
    if not active_connections:
        return

    data = json.dumps({**message, "timestamp": datetime.now(timezone.utc).isoformat()})
    dead = []

    for ws in active_connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)

    for ws in dead:
        disconnect(ws)


async def live_feed_loop():
    """
    Background task — pushes live updates every 30 seconds.
    Reads latest hostility scores and broadcasts to all clients.
    """
    from backend.m2_storage.database import SyncSessionLocal
    from backend.m2_storage.models.models import HostilityScore
    from sqlalchemy import desc

    while True:
        try:
            if active_connections:
                db = SyncSessionLocal()
                try:
                    latest = db.query(HostilityScore).order_by(
                        desc(HostilityScore.time)
                    ).limit(10).all()

                    scores = [
                        {
                            "country_a": s.country_a.iso_code,
                            "country_b": s.country_b.iso_code,
                            "score":     s.score,
                            "is_anomaly": s.is_anomaly,
                            "time":      s.time.isoformat(),
                        }
                        for s in latest
                    ]

                    await broadcast({
                        "type":   "hostility_update",
                        "scores": scores
                    })
                finally:
                    db.close()

        except Exception as e:
            logger.error(f"Live feed error: {e}")

        await asyncio.sleep(30)