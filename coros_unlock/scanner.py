"""BLE scanning on top of bleak.

macOS note: CoreBluetooth does not expose MAC addresses. bleak's
``device.address`` is a per-host UUID, and identification therefore relies on
the advertised name and/or the standard Heart Rate service. See
https://bleak.readthedocs.io/en/stable/backends/macos.html
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional, Tuple

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .config import Config

logger = logging.getLogger(__name__)

# Standard Bluetooth Heart Rate GATT service.
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"


def _name_of(device: BLEDevice, adv: AdvertisementData) -> str:
    return adv.local_name or device.name or ""


def _rssi_of(device: BLEDevice, adv: AdvertisementData) -> int:
    rssi = adv.rssi if adv.rssi is not None else device.rssi
    return rssi if rssi is not None else -127


def matches(device: BLEDevice, adv: AdvertisementData, config: Config) -> bool:
    """Decide whether an advertisement belongs to the configured watch."""
    rssi = _rssi_of(device, adv)
    if rssi < config.rssi_threshold:
        return False

    # Explicit per-host identifier is the strongest signal when available.
    if config.device_identifier and device.address == config.device_identifier:
        return True

    name = _name_of(device, adv)
    if config.device_name and config.device_name.lower() in name.lower():
        if config.require_hr_service:
            return HR_SERVICE_UUID in (adv.service_uuids or [])
        return True
    return False


async def list_devices(seconds: float = 8.0) -> List[Tuple[BLEDevice, AdvertisementData]]:
    """Passive scan used by the ``scan`` and ``pair`` commands."""
    found: dict[str, Tuple[BLEDevice, AdvertisementData]] = {}

    def _detect(device: BLEDevice, adv: AdvertisementData) -> None:
        found[device.address] = (device, adv)

    scanner = BleakScanner(detection_callback=_detect)
    async with scanner:
        await asyncio.sleep(seconds)
    return list(found.values())


class WatchScanner:
    """Continuous scanner that forwards watch detections to a callback."""

    def __init__(self, config: Config, on_detection) -> None:
        self._config = config
        self._on_detection = on_detection
        self._scanner: Optional[BleakScanner] = None

    def _detect(self, device: BLEDevice, adv: AdvertisementData) -> None:
        if matches(device, adv, self._config):
            logger.debug(
                "watch detected: name=%s address=%s rssi=%s services=%s",
                _name_of(device, adv),
                device.address,
                _rssi_of(device, adv),
                adv.service_uuids,
            )
            self._on_detection(device, adv)

    async def start(self) -> None:
        self._scanner = BleakScanner(detection_callback=self._detect)
        await self._scanner.start()
        logger.info("BLE scanner started")

    async def stop(self) -> None:
        if self._scanner is not None:
            await self._scanner.stop()
            self._scanner = None
