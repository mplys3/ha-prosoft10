"""Verify that polling reuses one BLE link and releases it on unload."""

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_coordinator():
    package = types.ModuleType("custom_components.prosoft10")
    package.__path__ = [
        str(Path(__file__).resolve().parents[1] / "custom_components" / "prosoft10")
    ]
    sys.modules.setdefault("custom_components.prosoft10", package)

    class FakeDataUpdateCoordinator:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, hass, _logger, **_kwargs):
            self.hass = hass
            self.data = None

    modules = {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.bluetooth": types.ModuleType(
            "homeassistant.components.bluetooth"
        ),
        "homeassistant.config_entries": types.ModuleType(
            "homeassistant.config_entries"
        ),
        "homeassistant.core": types.ModuleType("homeassistant.core"),
        "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.update_coordinator": types.ModuleType(
            "homeassistant.helpers.update_coordinator"
        ),
        "bleak_retry_connector": types.ModuleType("bleak_retry_connector"),
    }
    modules["homeassistant.components"].bluetooth = modules[
        "homeassistant.components.bluetooth"
    ]
    modules["homeassistant.components.bluetooth"].async_last_service_info = (
        lambda *_args, **_kwargs: None
    )
    modules["homeassistant.config_entries"].ConfigEntry = type("ConfigEntry", (), {})
    modules["homeassistant.core"].HomeAssistant = type("HomeAssistant", (), {})
    modules[
        "homeassistant.helpers.update_coordinator"
    ].DataUpdateCoordinator = FakeDataUpdateCoordinator
    modules["homeassistant.helpers.update_coordinator"].UpdateFailed = type(
        "UpdateFailed", (Exception,), {}
    )
    modules["bleak_retry_connector"].establish_connection = None
    with patch.dict(sys.modules, modules):
        sys.modules.pop("custom_components.prosoft10.coordinator", None)
        return importlib.import_module("custom_components.prosoft10.coordinator")


class CoordinatorTests(unittest.TestCase):
    def test_flow_alarm_expires_without_advertisements(self) -> None:
        module = _load_coordinator()
        entry = types.SimpleNamespace(data={"address": "AA:BB:CC:DD:EE:FF"})
        coordinator = module.ProsoftCoordinator(object(), entry)
        info = types.SimpleNamespace(manufacturer_data={65535: b"\x02\x00\x00"})
        with patch.object(module, "monotonic", return_value=100):
            coordinator._advertisement_received(info)
            self.assertTrue(coordinator.flow_alarm)
        with patch.object(module, "monotonic", return_value=401):
            self.assertIsNone(coordinator.flow_alarm)

    def test_reuses_connection_and_disconnects_on_close(self) -> None:
        async def run() -> None:
            module = _load_coordinator()
            self.assertEqual(module.POLL_INTERVAL.total_seconds(), 20)
            module.bluetooth.async_ble_device_from_address = lambda *_args, **_kwargs: (
                object()
            )
            clients = []

            class Client:
                def __init__(self, callback):
                    self.callback = callback
                    self.is_connected = True
                    self.notify_starts = 0
                    self.disconnects = 0

                async def start_notify(self, _uuid, _handler):
                    self.notify_starts += 1

                async def stop_notify(self, _uuid):
                    pass

                async def disconnect(self):
                    self.disconnects += 1
                    self.is_connected = False

            async def connect(_type, _device, _name, **kwargs):
                client = Client(kwargs["disconnected_callback"])
                clients.append(client)
                return client

            requested = []

            async def read(_client, code, _queue):
                requested.append(code)
                return code

            module.establish_connection = connect
            module.read_parameter = read
            entry = types.SimpleNamespace(data={"address": "AA:BB:CC:DD:EE:FF"})
            coordinator = module.ProsoftCoordinator(object(), entry)

            await coordinator._async_update_data()
            self.assertIn("1005", requested)
            requested.clear()
            await coordinator._async_update_data()
            self.assertNotIn("1005", requested)
            requested.clear()
            self.assertEqual(await coordinator.async_read_parameter("1146"), "1146")
            self.assertEqual(requested, ["1146"])
            self.assertIsNone(coordinator.data)
            self.assertEqual(len(clients), 1)
            self.assertEqual(clients[0].notify_starts, 1)
            self.assertEqual(clients[0].disconnects, 0)

            clients[0].is_connected = False
            clients[0].callback(clients[0])
            await coordinator._async_update_data()
            self.assertEqual(len(clients), 2)

            await coordinator.async_close()
            self.assertEqual(clients[1].disconnects, 1)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
