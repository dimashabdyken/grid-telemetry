from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from time import monotonic
from typing import Any

import orjson
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.core.cache import cache_get, cache_set, close_redis, get_redis
from backend.core.config import settings
from backend.db.base import AsyncSessionLocal
from backend.db.models import WarningEvent
from backend.schemas.telemetry import TelemetryRecordSchema
from backend.services.f1_service import f1_service
from backend.workers.telemetry_worker import (
    compute_vehicle_health,
    poll_telemetry,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logging.getLogger("requests_cache.session").setLevel(logging.ERROR)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._last_activity: dict[WebSocket, float] = {}

    async def connect(self, ws: WebSocket, room: str) -> None:
        await ws.accept()
        self._connections.setdefault(room, []).append(ws)
        self.touch_activity(ws)

    def disconnect(self, ws: WebSocket, room: str) -> None:
        sockets = self._connections.get(room)
        if not sockets:
            self._last_activity.pop(ws, None)
            return

        if ws in sockets:
            sockets.remove(ws)

        if not sockets:
            self._connections.pop(room, None)

        self._last_activity.pop(ws, None)

    def touch_activity(self, ws: WebSocket) -> None:
        self._last_activity[ws] = monotonic()

    def seconds_since_activity(self, ws: WebSocket) -> float:
        last_seen = self._last_activity.get(ws)
        if last_seen is None:
            return float("inf")
        return max(0.0, monotonic() - last_seen)

    def is_connected(self, ws: WebSocket, room: str) -> bool:
        return ws in self._connections.get(room, [])

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
PING_INTERVAL_SECONDS = 15.0
HEARTBEAT_TIMEOUT_SECONDS = 30.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except TypeError, ValueError:
        return default


def _to_optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except TypeError, ValueError:
        return None

    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return default


def _validate_telemetry_record(
    record: dict[str, Any],
    fallback_id: int,
) -> dict[str, Any]:
    payload = dict(record)

    date_value = payload.get("date")
    if not isinstance(date_value, str):
        payload["date"] = (
            date_value.isoformat()
            if hasattr(date_value, "isoformat")
            else str(date_value)
        )

    raw_id = payload.get("_id")
    payload["_id"] = _to_int(raw_id, fallback_id)

    return TelemetryRecordSchema.model_validate(payload).model_dump(by_alias=True)


def _validate_telemetry_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _validate_telemetry_record(record, fallback_id=index)
        for index, record in enumerate(records)
    ]


def _default_session_key() -> str:
    return (
        f"{settings.FASTF1_DEFAULT_YEAR}-"
        f"{settings.FASTF1_DEFAULT_EVENT}-"
        f"{settings.FASTF1_DEFAULT_SESSION}"
    )


async def fetch_session(session_key: str | int = "9161") -> dict[str, Any]:
    return {
        "session_key": session_key,
        "session_name": "Singapore Grand Prix",
        "session_type": "Race",
        "year": 2023,
    }


async def fetch_drivers(session_key: str | int) -> list[dict[str, Any]]:
    try:
        # Use a short timeout so driver loading cannot block the UI.
        data = await asyncio.wait_for(
            asyncio.to_thread(f1_service.get_drivers),
            timeout=2.0,
        )
        if data:
            return data
    except Exception:
        pass

    # Fallback mock so UI driver card never remains in loading state.
    return [
        {
            "driver_number": 1,
            "full_name": "Max Verstappen",
            "name_acronym": "VER",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
            "headshot_url": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/M/MAXVER01_Max_Verstappen/maxver01.png.transform/2col/image.png",
        }
    ]


async def fetch_car_data(
    _: str | int,
    driver_number: int | None = None,
) -> list[dict[str, Any]]:
    resolved_driver = driver_number if driver_number is not None else 1

    car_data = await asyncio.to_thread(
        f1_service.get_car_data_with_position,
        str(resolved_driver),
    )
    if car_data is None or car_data.empty:
        return []

    records: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(car_data.iterrows()):
        date_value = row.get("Date")
        date_iso = (
            str(date_value.isoformat()) if hasattr(date_value, "isoformat") else ""
        )
        gear = _to_int(row.get("nGear"))
        records.append(
            {
                "session_key": _default_session_key(),
                "date": date_iso,
                "driver_number": resolved_driver,
                "speed": _to_float(row.get("Speed")),
                "throttle": _to_float(row.get("Throttle")),
                "brake": _to_float(row.get("Brake")),
                "rpm": _to_int(row.get("RPM")),
                "gear": gear,
                "n_gear": gear,
                "drs": _to_int(row.get("DRS")),
                "x": _to_optional_float(row.get("X")),
                "y": _to_optional_float(row.get("Y")),
                "_id": index,
            }
        )

    return records


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


@app.get("/api/v1/sessions/{session_key}")
async def get_session(session_key: str) -> dict[str, Any]:
    cache_key = f"session_v2:{session_key}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    session = await fetch_session(session_key=session_key)
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
        cached_response = dict(cached)
        cached_records = cached_response.get("records", [])
        if isinstance(cached_records, list):
            cached_response["records"] = _validate_telemetry_records(cached_records)
        if include_health:
            return cached_response
        stripped = dict(cached_response)
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
            detail=f"FastF1 request failed: {exc}",
        ) from exc

    recent_records = records[-50:]
    validated_records = _validate_telemetry_records(recent_records)
    response: dict[str, Any] = {
        "session_key": resolved_session_key,
        "driver_number": driver_number,
        "count": len(validated_records),
        "records": validated_records,
    }
    if include_health:
        response["health"] = compute_vehicle_health(validated_records)

    await cache_set(cache_key, response)
    return response


@app.get("/api/v1/circuit/{session_key}")
async def get_circuit_path(session_key: str) -> dict[str, Any]:
    resolved_session_key = await _resolve_session_key(session_key)
    path = await asyncio.to_thread(f1_service.get_circuit_path)
    return {
        "session_key": resolved_session_key,
        "path": path,
        "count": len(path),
    }


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


@app.get("/api/v1/tyres")
async def get_tyres(session_key: str = "latest", driver_number: int = 1):
    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(f1_service.get_tyre_status, str(driver_number)),
            timeout=2.0,
        )
        if data.get("compound") and data.get("compound") != "UNKNOWN":
            return data
    except Exception:
        pass

    # Replay-safe fallback while FastF1 warms up.
    return {"compound": "MEDIUM", "life": 22}


@app.get("/api/v1/warnings/history")
async def get_warnings_history(session_key: str = "9161", limit: int = 10):
    async with AsyncSessionLocal() as db:
        stmt = (
            select(WarningEvent)
            .where(WarningEvent.session_key == session_key)
            .order_by(WarningEvent.triggered_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


async def _ws_ping_loop(websocket: WebSocket, room: str) -> None:
    while True:
        await asyncio.sleep(PING_INTERVAL_SECONDS)
        if not manager.is_connected(websocket, room):
            return
        if manager.seconds_since_activity(websocket) > HEARTBEAT_TIMEOUT_SECONDS:
            raise TimeoutError("WebSocket heartbeat timeout")
        try:
            await websocket.send_text(orjson.dumps({"type": "ping"}).decode("utf-8"))
        except WebSocketDisconnect, RuntimeError:
            # The connection is closing/closed; exit ping loop without escalating.
            return


async def _ws_receive_loop(websocket: WebSocket, room: str) -> None:
    while True:
        if not manager.is_connected(websocket, room):
            return
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break

        if message.get("type") != "websocket.receive" or "text" not in message:
            continue

        manager.touch_activity(websocket)

        text_payload = message["text"]
        try:
            parsed = orjson.loads(text_payload)
        except Exception:
            continue

        if isinstance(parsed, dict) and parsed.get("type") == "pong":
            manager.touch_activity(websocket)


async def _ws_telemetry_loop(
    websocket: WebSocket,
    room: str,
    session_key: str,
    driver_number: int,
) -> None:
    record_counter = 0
    async for payload in poll_telemetry(
        session_key=session_key,
        driver_number=driver_number,
    ):
        if not manager.is_connected(websocket, room):
            return

        outbound_payload = dict(payload)
        latest_record = outbound_payload.get("latest")
        if isinstance(latest_record, dict):
            required_fields = {
                "driver_number",
                "speed",
                "throttle",
                "brake",
                "rpm",
                "n_gear",
                "drs",
            }
            if required_fields.issubset(latest_record.keys()):
                outbound_payload["latest"] = _validate_telemetry_record(
                    latest_record,
                    fallback_id=record_counter,
                )
                record_counter += 1

        await manager.broadcast(room, outbound_payload)


@app.websocket("/ws/telemetry/{session_key}/{driver_number}")
async def telemetry_stream(
    websocket: WebSocket,
    session_key: str,
    driver_number: int,
) -> None:
    room = f"{session_key}:{driver_number}"
    ping_task: asyncio.Task[None] | None = None
    receive_task: asyncio.Task[None] | None = None
    telemetry_task: asyncio.Task[None] | None = None

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
    ping_task = asyncio.create_task(_ws_ping_loop(websocket, room))
    receive_task = asyncio.create_task(_ws_receive_loop(websocket, room))
    telemetry_task = asyncio.create_task(
        _ws_telemetry_loop(websocket, room, session_key, driver_number)
    )

    try:
        tasks = [task for task in (ping_task, receive_task, telemetry_task) if task]
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
        for task in pending:
            with suppress(asyncio.CancelledError):
                await task

        for task in done:
            exc = task.exception()
            if exc is None:
                continue
            if isinstance(exc, (WebSocketDisconnect, TimeoutError)):
                manager.disconnect(websocket, room)
                return
            raise exc
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except TimeoutError:
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
        for task in (ping_task, receive_task, telemetry_task):
            if task is None:
                continue
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        manager.disconnect(websocket, room)
