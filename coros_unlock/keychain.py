"""macOS Keychain integration via the ``security`` command-line tool.

The password is never written to a config file or log line. Every call uses an
argument list (no shell), so special characters cannot be interpreted.
"""

from __future__ import annotations

import getpass
import subprocess


class KeychainError(RuntimeError):
    pass


def store_password(password: str, account: str | None = None, service: str = "coros-unlock") -> None:
    """Create or update (-U) a generic password item."""
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-a",
                account or getpass.getuser(),
                "-s",
                service,
                "-w",
                password,
                "-U",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise KeychainError(exc.stderr.strip() or "failed to store password") from exc


def get_password(account: str | None = None, service: str = "coros-unlock") -> str:
    try:
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account or getpass.getuser(),
                "-s",
                service,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise KeychainError("this command is only available on macOS") from exc
    except subprocess.CalledProcessError as exc:
        raise KeychainError(
            exc.stderr.strip() or "password not found; run `coros-unlock password`"
        ) from exc
    return proc.stdout.rstrip("\n")


def delete_password(account: str | None = None, service: str = "coros-unlock") -> None:
    try:
        subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-a",
                account or getpass.getuser(),
                "-s",
                service,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise KeychainError(exc.stderr.strip() or "failed to delete password") from exc
