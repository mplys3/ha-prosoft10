"""Check the one-off read action without a Home Assistant installation."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        const.Platform = types.SimpleNamespace(
            SENSOR="sensor", BINARY_SENSOR="binary_sensor"
        )
        core = types.ModuleType("homeassistant.core")
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


if __name__ == "__main__":
    unittest.main()
