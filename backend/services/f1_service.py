from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock, Thread
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
        self._load_started = False
        self._load_start_lock = Lock()

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
                    session.load(telemetry=True, laps=True, weather=False)
                    self._session = session
        return self._session

    def get_session(self) -> Any:
        return self._load_session_once()

    def start_background_load(self) -> None:
        if self._session is not None or self._load_started:
            return

        with self._load_start_lock:
            if self._session is not None or self._load_started:
                return

            self._load_started = True

            def _load() -> None:
                try:
                    self._load_session_once()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("FastF1 background load failed: %s", exc)
                finally:
                    with self._load_start_lock:
                        if self._session is None:
                            self._load_started = False

            Thread(target=_load, daemon=True).start()

    @property
    def session(self) -> Any | None:
        return self._session

    def get_car_data(self, driver_number: str) -> Any:
        session = self._load_session_once()
        requested_driver = str(driver_number or "1")
        try:
            laps = session.laps.pick_driver(requested_driver)
            if not laps.empty:
                return laps.get_telemetry()
        except Exception:
            pass

        return session.car_data.get(requested_driver)

    def get_circuit_path(self) -> list[dict]:
        try:
            session = self._load_session_once()
            # Load circuit info.
            circuit_info = session.get_circuit_info()
            if circuit_info is None or not hasattr(circuit_info, "pos"):
                return []

            # pos is usually a numpy array or DataFrame of X, Y coordinates.
            import numpy as np

            x = (
                circuit_info.pos[:, 0]
                if isinstance(circuit_info.pos, np.ndarray)
                else circuit_info.pos["X"].values
            )
            y = (
                circuit_info.pos[:, 1]
                if isinstance(circuit_info.pos, np.ndarray)
                else circuit_info.pos["Y"].values
            )

            return [
                {"x": float(x_val), "y": float(y_val)}
                for x_val, y_val in zip(x, y)
            ]
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to load circuit path: %s", exc)
            return []

    def get_tyre_status(self, driver_number: str) -> dict[str, str | int]:
        self.start_background_load()
        if not self._session or self._session.laps.empty:
            return {"compound": "UNKNOWN", "life": 0}

        # Get laps for the specific driver.
        driver_laps = self._session.laps.pick_driver(str(driver_number))
        if driver_laps.empty:
            return {"compound": "UNKNOWN", "life": 0}

        # Keep only laps that have a known compound so we can infer current tyre.
        valid_laps = driver_laps.dropna(subset=["Compound"])
        if valid_laps.empty:
            return {"compound": "UNKNOWN", "life": 0}

        last_lap = valid_laps.iloc[-1]

        import pandas as pd

        tyre_life = last_lap.get("TyreLife", 0)
        if pd.isna(tyre_life):
            tyre_life = 0

        return {
            "compound": str(last_lap["Compound"]),
            "life": int(tyre_life),
        }

    def get_drivers(self) -> list[dict[str, Any]]:
        self.start_background_load()
        if self.session is None or not hasattr(self.session, "drivers"):
            return []

        drivers: list[dict[str, Any]] = []
        for drv in sorted(self.session.drivers):
            drv_code = str(drv)
            try:
                details = self.session.get_driver(drv_code)
            except Exception:
                details = {}

            drivers.append(
                {
                    "driver_number": int(drv_code) if str(drv_code).isdigit() else 0,
                    "full_name": details.get("FullName")
                    or details.get("Abbreviation")
                    or drv_code,
                    "name_acronym": details.get("Abbreviation") or drv_code,
                    "team_name": details.get("TeamName") or "",
                    "team_colour": details.get("TeamColor") or "ffffff",
                    "headshot_url": details.get("HeadshotUrl")
                    or "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/M/MAXVER01_Max_Verstappen/maxver01.png.transform/2col/image.png",
                }
            )

        return drivers


f1_service = F1Service()
