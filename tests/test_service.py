"""Check the one-off read action without a Home Assistant installation."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import voluptuous as vol


class ReadParameterServiceTests(unittest.TestCase):
    def test_returns_raw_value_without_creating_sensor_state(self) -> None:
        package_dir = (
            Path(__file__).resolve().parents[1] / "custom_components" / "prosoft10"
        )
        homeassistant = types.ModuleType("homeassistant")
        config_entries = types.ModuleType("homeassistant.config_entries")
        config_entries.ConfigEntry = type("ConfigEntry", (), {})
        const = types.ModuleType("homeassistant.const")
        const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
        const.Platform = types.SimpleNamespace(
            SENSOR="sensor", BINARY_SENSOR="binary_sensor"
        )
        core = types.ModuleType("homeassistant.core")
        core.callback = lambda func: func
        core.HomeAssistant = type("HomeAssistant", (), {})
        core.ServiceCall = type("ServiceCall", (), {})
        core.SupportsResponse = types.SimpleNamespace(ONLY="only")
        exceptions = types.ModuleType("homeassistant.exceptions")
        exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
        exceptions.ServiceValidationError = type(
            "ServiceValidationError", (Exception,), {}
        )
        coordinator_module = types.ModuleType("custom_components.prosoft10.coordinator")
        coordinator_module.ProsoftCoordinator = type("ProsoftCoordinator", (), {})
        modules = {
            "custom_components.prosoft10.coordinator": coordinator_module,
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.const": const,
            "homeassistant.core": core,
            "homeassistant.exceptions": exceptions,
        }

        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location(
                "custom_components.prosoft10",
                package_dir / "__init__.py",
                submodule_search_locations=[str(package_dir)],
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules["custom_components.prosoft10"] = module
            spec.loader.exec_module(module)

            registered = {}

            def register(_domain, _name, handler, **kwargs):
                registered["handler"] = handler
                registered.update(kwargs)

            hass = types.SimpleNamespace(
                data={}, services=types.SimpleNamespace(async_register=register)
            )
            asyncio.run(module.async_setup(hass, {}))
            self.assertEqual(registered["supports_response"], "only")
            schema = registered["schema"]
            self.assertEqual(schema({"code": 1146}), {"code": "1146"})
            with self.assertRaises(vol.Invalid):
                schema({"code": "@1146"})

            reader = AsyncMock(return_value="4321")
            hass.data["prosoft10"]["entry"] = types.SimpleNamespace(
                address="AA:BB:CC:DD:EE:FF", async_read_parameter=reader
            )
            call = types.SimpleNamespace(data=schema({"code": "1146"}))
            self.assertEqual(
                asyncio.run(registered["handler"](call)),
                {"code": "1146", "value": "4321"},
            )
            reader.assert_awaited_once_with("1146")

            async def check_lifecycle():
                for scenario in ("stop", "unload", "failed", "cancelled"):
                    with self.subTest(scenario=scenario):
                        listeners = []
                        unload_callbacks = []
                        removals = []

                        def listen(event, handler, listeners=listeners, removals=removals):
                            self.assertEqual(event, "homeassistant_stop")
                            listeners.append(handler)

                            def unsubscribe():
                                # Model HA: removing an unknown listener fails.
                                listeners.remove(handler)
                                removals.append(handler)

                            return unsubscribe

                        coordinator = types.SimpleNamespace(
                            start_advertisements=Mock(),
                            async_config_entry_first_refresh=AsyncMock(),
                            async_close=AsyncMock(),
                        )
                        module.ProsoftCoordinator = Mock(return_value=coordinator)
                        hass.bus = types.SimpleNamespace(async_listen=listen)
                        hass.config_entries = types.SimpleNamespace(
                            async_forward_entry_setups=AsyncMock(),
                            async_unload_platforms=AsyncMock(return_value=True),
                        )
                        entry = types.SimpleNamespace(
                            entry_id="new", async_on_unload=unload_callbacks.append
                        )
                        if scenario in ("failed", "cancelled"):
                            error = (
                                RuntimeError("first refresh failed")
                                if scenario == "failed" else asyncio.CancelledError()
                            )
                            coordinator.async_config_entry_first_refresh.side_effect = error
                            with self.assertRaises(type(error)):
                                await module.async_setup_entry(hass, entry)
                            coordinator.async_close.assert_awaited_once()
                        else:
                            await module.async_setup_entry(hass, entry)
                            if scenario == "stop":
                                await listeners[0](None)
                                coordinator.async_close.assert_awaited_once()
                            self.assertTrue(await module.async_unload_entry(hass, entry))
                        for cleanup in unload_callbacks:
                            cleanup()
                            cleanup()
                        self.assertEqual(listeners, [])
                        self.assertEqual(len(removals), 1)

            asyncio.run(check_lifecycle())



if __name__ == "__main__":
    unittest.main()
