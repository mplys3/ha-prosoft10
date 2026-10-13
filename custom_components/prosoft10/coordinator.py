"""Polling coordinator for ProSOFT 10."""

from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.exc import BleakError
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CHARACTERISTIC_UUID, POLL_INTERVAL, READ_CODES
from .protocol import ProtocolError, notification_handler, read_parameter

_LOGGER = logging.getLogger(__name__)


class ProsoftCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Fetch confirmed read-only fields in one BLE connection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ProSOFT 10",
            update_interval=POLL_INTERVAL,
        )
        self.address = entry.data["address"]

    async def _async_update_data(self) -> dict[str, str]:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise UpdateFailed(f"Bluetooth device {self.address} is out of range")

        values: dict[str, str] = {}
        queue: asyncio.Queue[bytes] = asyncio.Queue()
        try:
            async with BleakClient(device, timeout=15.0) as client:
                await client.start_notify(
                    CHARACTERISTIC_UUID, notification_handler(queue)
                )
                for code in READ_CODES:
                    try:
                        values[code] = await read_parameter(client, code, queue)
                    except (ProtocolError, BleakError, TimeoutError) as error:
                        _LOGGER.debug("Parameter %s unavailable: %s", code, error)
                await client.stop_notify(CHARACTERISTIC_UUID)
        except (BleakError, TimeoutError, OSError) as error:
            raise UpdateFailed(
                f"Unable to communicate with {self.address}: {error}"
            ) from error

        if not values:
            raise UpdateFailed("ProSOFT 10 did not answer any read requests")
        return values
