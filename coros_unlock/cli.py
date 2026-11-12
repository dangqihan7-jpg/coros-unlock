"""Command-line interface for coros-unlock."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import os
import sys
import time
from pathlib import Path

from . import __version__
from .config import DEFAULT_CONFIG_PATH, Config
from .presence import PresenceMonitor
from .scanner import WatchScanner, list_devices, _name_of, _rssi_of

logger = logging.getLogger("coros_unlock")

PLIST_LABEL = "com.corosunlock.daemon"
PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>coros_unlock</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{home}/Library/Logs/coros-unlock.log</string>
    <key>StandardErrorPath</key>
    <string>{home}/Library/Logs/coros-unlock.log</string>
</dict>
</plist>
"""


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_scan(args: argparse.Namespace) -> int:
    async def _run() -> int:
        results = await list_devices(args.duration)
        if not results:
            print("No BLE devices found. Make sure Bluetooth is on.")
            return 0
        print(f"{'#':>2}  {'RSSI':>5}  {'Address':<38}  Name")
        for i, (device, adv) in enumerate(results):
            print(
                f"{i:>2}  {_rssi_of(device, adv):>5}  {device.address:<38}  "
                f"{_name_of(device, adv) or '(unnamed)'}"
            )
        return 0

    return asyncio.run(_run())


def cmd_pair(args: argparse.Namespace) -> int:
    cfg = Config.load(args.config)

    async def _run() -> int:
        results = await list_devices(args.duration)
        if not results:
            print("No BLE devices found.")
            return 1
        for i, (device, adv) in enumerate(results):
            print(
                f"{i:>2}  {_rssi_of(device, adv):>5}  {device.address:<38}  "
                f"{_name_of(device, adv) or '(unnamed)'}"
            )
        choice = input("Pick the watch number (q to quit): ").strip()
        if choice.lower() == "q":
            return 1
        device, adv = results[int(choice)]
        cfg.device_name = _name_of(device, adv)
        cfg.device_identifier = device.address
        if args.hr_only:
            cfg.require_hr_service = True
        cfg.save(args.config)
        print(f"Saved to {args.config}: {cfg.device_name} ({cfg.device_identifier})")
        return 0

    return asyncio.run(_run())


def cmd_password(args: argparse.Namespace) -> int:
    from . import keychain

    pwd = getpass.getpass("Mac login password: ")
    if not pwd:
        print("Empty password, aborted.")
        return 1
    confirm = getpass.getpass("Confirm: ")
    if pwd != confirm:
        print("Passwords do not match.")
        return 1
    keychain.store_password(pwd)
    print("Stored in macOS Keychain under service 'coros-unlock'.")
    return 0


async def _run_daemon(cfg: Config) -> None:
    from . import keychain, lockscreen, unlocker

    monitor = PresenceMonitor(cfg.present_after, cfg.absent_after)
    last_unlock = 0.0

    async def handle_present() -> None:
        nonlocal last_unlock
        now = time.monotonic()
        if now - last_unlock < cfg.unlock_cooldown:
            return
        if not lockscreen.is_locked():
            return
        try:
            password = keychain.get_password()
            await unlocker.unlock_with_retry(password)
            last_unlock = time.monotonic()
            logger.info("unlock submitted")
        except Exception as exc:  # never let the daemon die
            logger.error("unlock failed: %s", exc)

    def on_detection(device, adv) -> None:
        if monitor.mark_detection() == "present":
            asyncio.ensure_future(handle_present())

    async def ticker() -> None:
        from . import lockscreen

        while True:
            await asyncio.sleep(1)
            if monitor.tick() == "absent" and cfg.lock_when_away:
                lockscreen.lock()
                logger.info("watch away: display locked")

    scanner = WatchScanner(cfg, on_detection)
    await scanner.start()
    try:
        await ticker()
    finally:
        await scanner.stop()


def cmd_daemon(args: argparse.Namespace) -> int:
    if sys.platform != "darwin":
        print("The daemon only runs on macOS.", file=sys.stderr)
        return 1
    cfg = Config.load(args.config)
    if not cfg.device_name and not cfg.device_identifier:
        print("No watch paired. Run `coros-unlock pair` first.", file=sys.stderr)
        return 1
    _setup_logging(cfg.log_level)
    try:
        asyncio.run(_run_daemon(cfg))
    except KeyboardInterrupt:
        pass
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    if sys.platform != "darwin":
        print("launchd installation is only available on macOS.", file=sys.stderr)
        return 1
    agents = Path.home() / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    plist_path = agents / f"{PLIST_LABEL}.plist"
    plist_path.write_text(
        PLIST_TEMPLATE.format(
            label=PLIST_LABEL,
            python=sys.executable,
            home=str(Path.home()),
        ),
        encoding="utf-8",
    )
    print(f"Installed {plist_path}")
    print("Load it with:")
    print(f"  launchctl bootstrap gui/$(id -u) {plist_path}")
    print("Logs: ~/Library/Logs/coros-unlock.log")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
    if plist_path.exists():
        plist_path.unlink()
        print(f"Removed {plist_path}")
    else:
        print("No launchd plist found.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cfg = Config.load(args.config)
    print(f"config file : {args.config}")
    print(f"device name : {cfg.device_name or '(not set)'}")
    print(f"identifier  : {cfg.device_identifier or '(not set)'}")
    print(f"HR only     : {cfg.require_hr_service}")
    print(f"lock away   : {cfg.lock_when_away}")
    if sys.platform == "darwin":
        import subprocess

        proc = subprocess.run(
            ["security", "find-generic-password", "-s", "coros-unlock"],
            capture_output=True,
        )
        print("keychain    :", "present" if proc.returncode == 0 else "missing")
        try:
            from . import lockscreen

            print("locked now  :", lockscreen.is_locked())
        except RuntimeError as exc:
            print(f"locked now  : unknown ({exc})")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coros-unlock",
        description="Unlock a Mac when a COROS watch is in BLE range.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="config file path",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="scan BLE devices for a few seconds")
    p_scan.add_argument("--duration", type=float, default=8.0)
    p_scan.set_defaults(func=cmd_scan)

    p_pair = sub.add_parser("pair", help="pair a watch and save its identity")
    p_pair.add_argument("--duration", type=float, default=8.0)
    p_pair.add_argument(
        "--hr-only",
        action="store_true",
        help="require the Heart Rate service (watch in Broadcast HR mode)",
    )
    p_pair.set_defaults(func=cmd_pair)

    p_pwd = sub.add_parser("password", help="store Mac login password in Keychain")
    p_pwd.set_defaults(func=cmd_password)

    p_daemon = sub.add_parser("daemon", help="run the proximity daemon in foreground")
    p_daemon.set_defaults(func=cmd_daemon)

    p_install = sub.add_parser("install", help="install the launchd agent")
    p_install.set_defaults(func=cmd_install)

    p_uninstall = sub.add_parser("uninstall", help="remove the launchd agent")
    p_uninstall.set_defaults(func=cmd_uninstall)

    p_status = sub.add_parser("status", help="show current configuration")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
