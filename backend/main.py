from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Any

import orjson
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.core.cache import cache_get, cache_set, close_redis, get_redis
from backend.core.config import settings
from backend.workers.telemetry_worker import (
    compute_vehicle_health,
    fetch_car_data,
    fetch_drivers,
    fetch_session,
    poll_telemetry,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, room: str) -> None:
        await ws.accept()
        self._connections.setdefault(room, []).append(ws)

    def disconnect(self, ws: WebSocket, room: str) -> None:
        sockets = self._connections.get(room)
        if not sockets:
            return

        if ws in sockets:
            sockets.remove(ws)

        if not sockets:
            self._connections.pop(room, None)

    async def broadcast(self, room: str, payload: dict[str, Any]) -> None:
        sockets = list(self._connections.get(room, []))
        if not sockets:
            return

        message = orjson.dumps(payload).decode("utf-8")
        disconnected: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws, room)

    @property
    def active_rooms(self) -> int:
        return sum(1 for sockets in self._connections.values() if sockets)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_client = await get_redis()
    logger.info(
        "Starting %s v%s (redis=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        bool(redis_client),
    )
    try:
        yield
    finally:
        await close_redis()
        logger.info("Shutdown complete for %s", settings.APP_NAME)


app = FastAPI(
    title="Grid Telemetry API",
    description="Production-grade F1 monitoring system",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _resolve_session_key(session_key: str | int) -> str | int:
    if session_key != "latest":
        return session_key
    latest = await fetch_session("latest")
    return latest.get("session_key", "latest")


@app.get("/")
async def read_root() -> dict[str, str]:
    return {
        "message": "Grid Telemetry API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    redis_ok = False
    redis_client = await get_redis()
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except Exception:
            redis_ok = False

    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "redis": redis_ok,
    }


@app.get("/api/v1/sessions/latest")
async def latest_session() -> dict[str, Any]:
    cache_key = "session:latest"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    session = await fetch_session("latest")
    if not session:
        raise HTTPException(status_code=404, detail="No session found")

    await cache_set(cache_key, session, ttl=30)
    return session


@app.get("/api/v1/telemetry")
async def telemetry(
    session_key: str = "latest",
    driver_number: int | None = Query(default=None),
    include_health: bool = True,
) -> dict[str, Any]:
    cache_key = f"telemetry:{session_key}:{driver_number}"
    cached = await cache_get(cache_key)
    if cached is not None:
        if include_health:
            return cached
        stripped = dict(cached)
        stripped.pop("health", None)
        return stripped

    try:
        resolved_session_key = await _resolve_session_key(session_key)
        records = await fetch_car_data(
            resolved_session_key,
            driver_number=driver_number,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenF1 request failed: {exc}",
        ) from exc

    recent_records = records[-50:]
    response: dict[str, Any] = {
        "session_key": resolved_session_key,
        "driver_number": driver_number,
        "count": len(recent_records),
        "records": recent_records,
    }
    if include_health:
        response["health"] = compute_vehicle_health(recent_records)

    await cache_set(cache_key, response)
    return response


@app.get("/api/v1/drivers")
async def drivers(session_key: str = "latest") -> dict[str, Any]:
    cache_key = f"drivers:{session_key}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    resolved_session_key = await _resolve_session_key(session_key)
    data = await fetch_drivers(resolved_session_key)
    payload = {
        "session_key": resolved_session_key,
        "drivers": data,
        "count": len(data),
    }
    await cache_set(cache_key, payload, ttl=60)
    return payload


async def _ws_ping_loop(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(15)
        await websocket.send_text(orjson.dumps({"type": "ping"}).decode("utf-8"))


@app.websocket("/ws/telemetry/{session_key}/{driver_number}")
async def telemetry_stream(
    websocket: WebSocket,
    session_key: str,
    driver_number: int,
) -> None:
    room = f"{session_key}:{driver_number}"
    ping_task: asyncio.Task[None] | None = None

    await manager.connect(websocket, room)
    await websocket.send_text(
        orjson.dumps(
            {
                "type": "connected",
                "session_key": session_key,
                "driver_number": driver_number,
            }
        ).decode("utf-8")
    )
    ping_task = asyncio.create_task(_ws_ping_loop(websocket))

    try:
        async for payload in poll_telemetry(
            session_key=session_key,
            driver_number=driver_number,
            interval_seconds=settings.OPENF1_POLL_INTERVAL,
        ):
            await manager.broadcast(room, payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception as exc:
        try:
            await websocket.send_text(
                orjson.dumps({"type": "error", "message": str(exc)}).decode("utf-8")
            )
        except Exception:
            pass
        manager.disconnect(websocket, room)
    finally:
        if ping_task is not None:
            ping_task.cancel()
            with suppress(asyncio.CancelledError):
                await ping_task
        manager.disconnect(websocket, room)
