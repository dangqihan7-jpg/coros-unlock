"""Presence state machine.

Deliberately independent of any BLE library so it can be unit tested with a
fake clock. The scanner feeds raw detections in; consumers only react to
debounced state transitions.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable, Optional


class PresenceState(str, Enum):
    UNKNOWN = "unknown"
    PRESENT = "present"
    ABSENT = "absent"


class PresenceMonitor:
    """Debounce noisy BLE advertisements into present/absent transitions."""

    def __init__(
        self,
        present_after: int = 2,
        absent_after: float = 15.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if present_after < 1:
            raise ValueError("present_after must be >= 1")
        if absent_after <= 0:
            raise ValueError("absent_after must be > 0")
        self._present_after = present_after
        self._absent_after = absent_after
        self._clock = clock
        self.state = PresenceState.UNKNOWN
        self._detection_count = 0
        self._last_seen: Optional[float] = None

    @property
    def last_seen(self) -> Optional[float]:
        return self._last_seen

    def mark_detection(self, rssi: Optional[int] = None) -> Optional[str]:
        """Register one advertisement. Returns a transition event or None."""
        now = self._clock()
        # A gap longer than absent_after means the streak is broken.
        if self._last_seen is not None and now - self._last_seen > self._absent_after:
            self._detection_count = 0
        self._last_seen = now
        self._detection_count += 1

        if self.state != PresenceState.PRESENT and self._detection_count >= self._present_after:
            self.state = PresenceState.PRESENT
            return PresenceState.PRESENT.value
        return None

    def tick(self) -> Optional[str]:
        """Advance time-based logic; call this roughly once per second."""
        if self.state == PresenceState.PRESENT and self._last_seen is not None:
            if self._clock() - self._last_seen > self._absent_after:
                self.state = PresenceState.ABSENT
                self._detection_count = 0
                return PresenceState.ABSENT.value
        return None
