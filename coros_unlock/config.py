"""Configuration loading and persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Union

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "coros-unlock"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
KEYCHAIN_SERVICE = "coros-unlock"


@dataclass
class Config:
    """User-tunable settings.

    Attributes:
        device_name: case-insensitive substring matched against the BLE
            advertised name (e.g. "COROS PACE 3").
        device_identifier: platform-specific address. On macOS this is the
            CoreBluetooth per-host UUID, not a MAC address.
        require_hr_service: only accept advertisements carrying the standard
            Heart Rate service (0x180D), i.e. watch in Broadcast HR mode.
        present_after: consecutive detections needed to mark the watch present.
        absent_after: seconds without a detection before marking it away.
        unlock_cooldown: minimum seconds between two unlock attempts.
        lock_when_away: lock the display when the watch leaves range.
        rssi_threshold: ignore advertisements weaker than this RSSI.
        log_level: logging level name.
    """

    device_name: str = ""
    device_identifier: str = ""
    require_hr_service: bool = False
    present_after: int = 2
    absent_after: float = 15.0
    unlock_cooldown: float = 30.0
    lock_when_away: bool = True
    rssi_threshold: int = -90
    log_level: str = "INFO"

    def save(self, path: Union[str, os.PathLike] = DEFAULT_CONFIG_PATH) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass

    @classmethod
    def load(cls, path: Union[str, os.PathLike] = DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in known})
