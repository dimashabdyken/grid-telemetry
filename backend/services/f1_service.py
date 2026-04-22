from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

import fastf1

from backend.core.config import settings

logger = logging.getLogger(__name__)


class F1Service:
    """Singleton service responsible for FastF1 session lifecycle."""

    _instance: ClassVar[F1Service | None] = None
    _instance_lock: ClassVar[Lock] = Lock()

    def __new__(cls) -> F1Service:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.year = settings.FASTF1_DEFAULT_YEAR
        self.event = settings.FASTF1_DEFAULT_EVENT
        self.session_name = settings.FASTF1_DEFAULT_SESSION
        self._session: Any | None = None
        self._session_lock = Lock()

        service_dir = Path(__file__).resolve().parent
        project_root = Path(__file__).resolve().parents[2]
        configured_cache_dir = Path(settings.FASTF1_CACHE_DIR)
        if not configured_cache_dir.is_absolute():
            configured_cache_dir = (service_dir / configured_cache_dir).resolve()
        self.cache_dir = configured_cache_dir
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback_cache_dir = (project_root / "cache").resolve()
            logger.warning(
                "FASTF1 cache dir '%s' is not writable, falling back to '%s'",
                self.cache_dir,
                fallback_cache_dir,
            )
            fallback_cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir = fallback_cache_dir
        fastf1.Cache.enable_cache(str(self.cache_dir))

        self._initialized = True

    def _load_session_once(self) -> Any:
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    session = fastf1.get_session(
                        self.year, self.event, self.session_name
                    )
                    session.load(telemetry=True, laps=False, weather=False)
                    self._session = session
        return self._session

    def get_session(self) -> Any:
        return self._load_session_once()

    def get_car_data(self, driver_number: str) -> Any:
        session = self._load_session_once()
        requested_driver = str(driver_number or "1")

        car_data = session.car_data.get(requested_driver)
        if car_data is not None and not car_data.empty:
            return car_data

        return session.car_data.get("1")


f1_service = F1Service()
