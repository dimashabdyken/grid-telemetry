from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

import fastf1


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

        self.year = 2023
        self.event = "Singapore"
        self.session_name = "R"
        self._session: Any | None = None
        self._session_lock = Lock()

        project_root = Path(__file__).resolve().parents[2]
        self.cache_dir = project_root / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(self.cache_dir))

        self._initialized = True

    def _load_session_once(self) -> Any:
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    session = fastf1.get_session(
                        self.year, self.event, self.session_name
                    )
                    try:
                        session.load(telemetry=True, laps=False, weather=False)
                    except Exception:
                        fastf1.Cache.clear_cache(str(self.cache_dir))
                        raise
                    self._session = session
        return self._session

    def get_car_data(self, driver_number: str) -> Any:
        session = self._load_session_once()
        requested_driver = str(driver_number or "1")

        car_data = session.car_data.get(requested_driver)
        if car_data is not None and not car_data.empty:
            return car_data

        return session.car_data.get("1")


f1_service = F1Service()
