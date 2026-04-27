from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock, Thread
from typing import Any, ClassVar

import fastf1
import pandas as pd

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
            if hasattr(session.laps, "pick_drivers"):
                laps = session.laps.pick_drivers([requested_driver])
            else:
                laps = session.laps[session.laps["DriverNumber"] == requested_driver]
            if not laps.empty:
                return laps.get_telemetry()
        except Exception:
            pass

        return session.car_data.get(requested_driver)

    def get_car_data_with_position(self, driver_number: str) -> Any:
        """Return telemetry merged with X/Y coordinates when available."""
        session = self._load_session_once()
        requested_driver = str(driver_number or "1")

        car_data = self.get_car_data(requested_driver)
        if car_data is None or getattr(car_data, "empty", True):
            return car_data

        pos_data = None
        try:
            pos_map = getattr(session, "pos_data", None)
            if isinstance(pos_map, dict):
                candidate_keys: list[Any] = [requested_driver]
                if requested_driver.isdigit():
                    candidate_keys.append(int(requested_driver))

                for key in candidate_keys:
                    if key in pos_map:
                        pos_data = pos_map.get(key)
                        break

                if pos_data is None:
                    # Handle mixed key typing from upstream providers.
                    for key, value in pos_map.items():
                        if str(key) == requested_driver:
                            pos_data = value
                            break
        except Exception:
            pos_data = None

        if pos_data is None or getattr(pos_data, "empty", True):
            if "X" not in car_data.columns:
                car_data = car_data.copy()
                car_data["X"] = pd.NA
            if "Y" not in car_data.columns:
                car_data = car_data.copy() if "X" in car_data.columns else car_data
                car_data["Y"] = pd.NA
            return car_data

        try:
            left = car_data.reset_index().rename(columns={"index": "Date"})
            right = pos_data.reset_index().rename(columns={"index": "Date"})

            # Keep only position columns needed for the frontend map.
            available_cols = [
                col for col in ("Date", "X", "Y", "Status") if col in right.columns
            ]
            right = right[available_cols].copy()

            left["Date"] = pd.to_datetime(left["Date"], errors="coerce")
            right["Date"] = pd.to_datetime(right["Date"], errors="coerce")
            left = left.dropna(subset=["Date"]).sort_values("Date")
            right = right.dropna(subset=["Date"]).sort_values("Date")

            if "Status" in right.columns:
                on_track = right[right["Status"] == "OnTrack"]
                if not on_track.empty:
                    right = on_track

            merged = pd.merge_asof(
                left,
                right,
                on="Date",
                direction="nearest",
            )

            if "X" not in merged.columns:
                merged["X"] = pd.NA
            if "Y" not in merged.columns:
                merged["Y"] = pd.NA

            merged["X"] = pd.to_numeric(merged["X"], errors="coerce")
            merged["Y"] = pd.to_numeric(merged["Y"], errors="coerce")

            # Keep positional continuity when some points are missing or late.
            merged["X"] = merged["X"].interpolate(limit_direction="both")
            merged["Y"] = merged["Y"].interpolate(limit_direction="both")
            merged["X"] = merged["X"].ffill().bfill()
            merged["Y"] = merged["Y"].ffill().bfill()

            if "Status" in merged.columns:
                merged = merged.drop(columns=["Status"])

            merged = merged.set_index("Date")
            return merged
        except Exception:
            fallback = car_data.copy()
            if "X" not in fallback.columns:
                fallback["X"] = pd.NA
            if "Y" not in fallback.columns:
                fallback["Y"] = pd.NA
            return fallback

    def get_circuit_path(self) -> list[dict]:
        try:
            session = self._load_session_once()
            circuit_info = session.get_circuit_info()

            def _points_from_xy_source(source: Any) -> list[dict[str, float]]:
                if source is None:
                    return []

                def _is_valid_track(points: list[dict[str, float]]) -> bool:
                    if len(points) < 20:
                        return False

                    xs = [point["x"] for point in points]
                    ys = [point["y"] for point in points]
                    x_span = max(xs) - min(xs)
                    y_span = max(ys) - min(ys)

                    # Reject collapsed/degenerate paths (commonly all (0, 0)).
                    return x_span > 1e-3 or y_span > 1e-3

                # Handle DataFrame-like X/Y payload.
                if (
                    hasattr(source, "columns")
                    and "X" in source.columns
                    and "Y" in source.columns
                ):
                    points_df = source
                    if "Status" in points_df.columns:
                        on_track = points_df[points_df["Status"] == "OnTrack"]
                        if not on_track.empty:
                            points_df = on_track

                    points_df = points_df[["X", "Y"]].dropna()
                    points_df = points_df[
                        (points_df["X"].abs() > 1e-6) | (points_df["Y"].abs() > 1e-6)
                    ]
                    points_df = points_df.drop_duplicates()
                    if points_df.empty:
                        return []

                    # Keep enough detail for shape while limiting payload size.
                    if len(points_df) > 4000:
                        points_df = points_df.iloc[::4]

                    points = [
                        {"x": float(x_val), "y": float(y_val)}
                        for x_val, y_val in points_df[["X", "Y"]].itertuples(
                            index=False
                        )
                    ]
                    return points if _is_valid_track(points) else []

                # Handle ndarray-like payload.
                if hasattr(source, "__getitem__"):
                    try:
                        points = [
                            {"x": float(point[0]), "y": float(point[1])}
                            for point in source
                            if not (
                                abs(float(point[0])) <= 1e-6
                                and abs(float(point[1])) <= 1e-6
                            )
                        ]
                        return points if _is_valid_track(points) else []
                    except Exception:
                        return []

                return []

            # Prefer dense position data so the frontend can animate smoothly.
            pos_data = getattr(session, "pos_data", None)
            if isinstance(pos_data, dict) and pos_data:
                preferred_keys = ["1"] + [key for key in pos_data if str(key) != "1"]
                for key in preferred_keys:
                    source = pos_data.get(key)
                    points = _points_from_xy_source(source)
                    if points:
                        return points

            # Fallback to static circuit geometry when position data is unavailable.
            for attr in ("pos", "corners", "marshal_lights", "marshal_sectors"):
                source = getattr(circuit_info, attr, None) if circuit_info else None
                points = _points_from_xy_source(source)
                if points:
                    return points

            return []
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to load circuit path: %s", exc)
            return []

    def get_tyre_status(self, driver_number: str) -> dict[str, str | int]:
        self.start_background_load()
        if not self._session or self._session.laps.empty:
            return {"compound": "UNKNOWN", "life": 0}

        # Get laps for the specific driver.
        if hasattr(self._session.laps, "pick_drivers"):
            driver_laps = self._session.laps.pick_drivers([str(driver_number)])
        else:
            driver_laps = self._session.laps[
                self._session.laps["DriverNumber"] == str(driver_number)
            ]
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
