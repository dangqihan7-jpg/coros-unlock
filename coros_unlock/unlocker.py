"""Type the stored password into the login window through Accessibility.

The password is passed as an osascript argv element (never embedded in script
text), so backslashes and quotes do not need escaping and cannot break out of
the argument. The host running the daemon must be granted Accessibility
permission in System Settings > Privacy & Security > Accessibility.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)

# key code 36 is Return on macOS.
_UNLOCK_SCRIPT = """
on run argv
    set thePassword to item 1 of argv
    tell application "System Events"
        keystroke thePassword
        key code 36
    end tell
end run
"""


def build_command(password: str) -> list[str]:
    """Exposed for tests: argv list with no shell and no embedded secret."""
    return ["osascript", "-e", _UNLOCK_SCRIPT, password]


def unlock(password: str) -> None:
    proc = subprocess.run(build_command(password), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript unlock failed")


async def unlock_with_retry(password: str, attempts: int = 2, delay: float = 1.0) -> None:
    """Retry once: the first keystrokes can land while the window is animating."""
    for attempt in range(1, attempts + 1):
        try:
            await asyncio.get_running_loop().run_in_executor(None, unlock, password)
            return
        except RuntimeError:
            if attempt == attempts:
                raise
            await asyncio.sleep(delay)
