"""Polling coordinator for ProSOFT 10."""

from __future__ import annotations

import asyncio
import logging
from time import monotonic

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .beacon import continuous_flow_alarm
from .const import CHARACTERISTIC_UUID, POLL_INTERVAL, READ_CODES, REGENERATION_TIMES
from .protocol import ProtocolError, notification_handler, read_parameter

_LOGGER = logging.getLogger(__name__)


class ProsoftCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Read confirmed fields through a persistent BLE connection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ProSOFT 10",
            update_interval=POLL_INTERVAL,
        )
        self.address = entry.data["address"]
        self._client: BleakClient | None = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._connection_lock = asyncio.Lock()
        self._cancel_advertisements = None
        self._flow_alarm: bool | None = None
        self._last_advertisement: float | None = None
        self._poll_count = 0

    @property
    def flow_alarm(self) -> bool | None:
        """The latest valid, recent NF-02 beacon flag."""
        if (
            self._last_advertisement is None
            or monotonic() - self._last_advertisement > 300
        ):
            return None
        return self._flow_alarm

    def start_advertisements(self) -> None:
        """Listen for the alarm flags without opening another Bluetooth scanner."""
        self._cancel_advertisements = bluetooth.async_register_callback(
            self.hass,
            self._advertisement_changed,
            {"address": self.address},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        self._refresh_advertisement()

    def _advertisement_changed(
        self,
        info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        """Receive changed advertisement payloads from Home Assistant."""
        self._advertisement_received(info)

    def _refresh_advertisement(self) -> None:
        """Refresh age even when the device repeats an identical advertisement."""
        latest = bluetooth.async_last_service_info(
            self.hass, self.address, connectable=False
        )
        if latest is not None and bluetooth.async_address_present(
            self.hass, self.address, connectable=False
        ):
            self._advertisement_received(latest)

    def _advertisement_received(
        self, info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Update the leak flag from the manufacturer's notification byte."""
        alarm = continuous_flow_alarm(info.manufacturer_data)
        if alarm is None:
            return
        changed = self._flow_alarm is None or alarm != self._flow_alarm
        self._flow_alarm = alarm
        self._last_advertisement = monotonic()
        if changed and self.data is not None:
            self.async_update_listeners()

    def _disconnected(self, client: BleakClient) -> None:
        """Forget a dropped client so the next poll creates a new one."""
        if self._client is client:
            _LOGGER.debug("ProSOFT 10 disconnected from Bluetooth")
            self._client = None

    async def _async_connect(self) -> BleakClient:
        """Connect once and subscribe to replies for the connection lifetime."""
        if self._client is not None and self._client.is_connected:
            return self._client

        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise UpdateFailed(f"Bluetooth device {self.address} is out of range")

        self._queue = asyncio.Queue()
        client = await establish_connection(
            BleakClient,
            device,
            "ProSOFT 10",
            disconnected_callback=self._disconnected,
            max_attempts=3,
            timeout=15.0,
            ble_device_callback=lambda: (
                bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                or device
            ),
        )
        self._client = client
        try:
            async with asyncio.timeout(10):
                await client.start_notify(
                    CHARACTERISTIC_UUID, notification_handler(self._queue)
                )
        except (Exception, asyncio.CancelledError):
            await self._async_disconnect(client)
            raise
        _LOGGER.debug("ProSOFT 10 Bluetooth connection ready")
        return client

    async def _async_disconnect(self, client: BleakClient | None = None) -> None:
        """Release notifications and the BLE link on unload or I/O failure."""
        if client is None:
            client = self._client
        if client is None:
            return
        if self._client is client:
            self._client = None
        if client.is_connected:
            try:
                async with asyncio.timeout(10):
                    await client.stop_notify(CHARACTERISTIC_UUID)
            except (BleakError, TimeoutError, OSError) as error:
                _LOGGER.debug("Could not stop ProSOFT 10 notifications: %s", error)
        try:
            async with asyncio.timeout(10):
                await client.disconnect()
        except (BleakError, TimeoutError, OSError) as error:
            _LOGGER.warning("Could not disconnect ProSOFT 10 cleanly: %s", error)

    async def async_close(self) -> None:
        """Close the connection when Home Assistant unloads the entry."""
        if self._cancel_advertisements is not None:
            self._cancel_advertisements()
            self._cancel_advertisements = None
        async with self._connection_lock:
            await self._async_disconnect()

    async def _async_update_data(self) -> dict[str, str]:
        async with self._connection_lock:
            values: dict[str, str] = {
                code: self.data[code]
                for code in REGENERATION_TIMES
                if self.data is not None and code in self.data
            }
            live_response = False
            try:
                client = await self._async_connect()
                codes = READ_CODES + (
                    REGENERATION_TIMES if self._poll_count % 15 == 0 else ()
                )
                for code in codes:
                    try:
                        values[code] = await read_parameter(client, code, self._queue)
                        live_response = True
                    except ProtocolError as error:
                        _LOGGER.debug("Parameter %s unavailable: %s", code, error)
            except (BleakError, TimeoutError, OSError) as error:
                await self._async_disconnect()
                raise UpdateFailed(
                    f"Unable to communicate with {self.address}: {error}"
                ) from error

            if not live_response:
                await self._async_disconnect()
                raise UpdateFailed("ProSOFT 10 did not answer any read requests")
            self._refresh_advertisement()
            self._poll_count += 1
            return values
