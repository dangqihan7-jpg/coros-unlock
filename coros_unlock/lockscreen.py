"""Lock state detection and display locking.

Requires the ``pyobjc-framework-Quartz`` package (installed automatically on
macOS). Only the in-session lock screen is observable; the FileVault pre-boot
environment is unreachable to third-party code by design.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def is_locked() -> bool:
    """Return True when the user session is currently locked."""
    try:
        import Quartz
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "pyobjc-framework-Quartz is required: pip install pyobjc-framework-Quartz"
        ) from exc

    info = Quartz.CGSessionCopyCurrentDictionary()
    if not info:
        return False
    return bool(info.get("CGSSessionScreenIsLocked", 0))


def lock() -> None:
    """Put the display to sleep (with immediate password requirement on wake)."""
    try:
        subprocess.run(["pmset", "displaysleepnow"], check=True, capture_output=True)
    except FileNotFoundError:
        logger.warning("pmset not found; skipping lock action")
