"""Ensure the sensor platform loads without a nonexistent time device class."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class SensorImportTests(unittest.TestCase):
    def test_regeneration_time_is_a_plain_text_sensor(self) -> None:
        package_dir = (
            Path(__file__).resolve().parents[1] / "custom_components" / "prosoft10"
        )
        sensor = types.ModuleType("homeassistant.components.sensor")
        sensor.SensorDeviceClass = types.SimpleNamespace(
            WEIGHT="weight", WATER="water", ENUM="enum"
        )
        sensor.SensorEntity = type("SensorEntity", (), {})
        sensor.SensorStateClass = types.SimpleNamespace(
            MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing"
        )
        const = types.ModuleType("homeassistant.const")
        const.PERCENTAGE = "%"
        const.UnitOfMass = types.SimpleNamespace(KILOGRAMS="kg")
        const.UnitOfVolume = types.SimpleNamespace(LITERS="L", CUBIC_METERS="m³")
        registry = types.ModuleType("homeassistant.helpers.device_registry")
        registry.CONNECTION_BLUETOOTH = "bluetooth"
        registry.DeviceInfo = dict
        platform = types.ModuleType("homeassistant.helpers.entity_platform")
        platform.AddConfigEntryEntitiesCallback = object
        update = types.ModuleType("homeassistant.helpers.update_coordinator")

        class CoordinatorEntity:
            def __class_getitem__(cls, _item):
                return cls

            def __init__(self, coordinator):
                self.coordinator = coordinator

        update.CoordinatorEntity = CoordinatorEntity
        modules = {
            "homeassistant.components.sensor": sensor,
            "homeassistant.config_entries": types.ModuleType(
                "homeassistant.config_entries"
            ),
            "homeassistant.const": const,
            "homeassistant.core": types.ModuleType("homeassistant.core"),
            "homeassistant.helpers.device_registry": registry,
            "homeassistant.helpers.entity_platform": platform,
            "homeassistant.helpers.update_coordinator": update,
        }
        modules["homeassistant.config_entries"].ConfigEntry = object
        modules["homeassistant.core"].HomeAssistant = object
        coordinator_module = types.ModuleType("custom_components.prosoft10.coordinator")
        coordinator_module.ProsoftCoordinator = object
        modules["custom_components.prosoft10.coordinator"] = coordinator_module

        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location(
                "custom_components.prosoft10.sensor", package_dir / "sensor.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            coordinator = types.SimpleNamespace(
                address="AA:BB:CC:DD:EE:FF", data={"1017": "02:30", "1018": "99:99"}
            )
            self.assertEqual(
                module.ProsoftRegenerationTime(coordinator, 1, "1017").native_value,
                "02:30",
            )
            self.assertIsNone(
                module.ProsoftRegenerationTime(coordinator, 2, "1018").native_value
            )
            coordinator.data["1005"] = "1.25"
            salt = module.ProsoftSaltPerRegeneration(coordinator)
            self.assertEqual(salt.native_value, 1.25)
            self.assertEqual(salt._attr_native_unit_of_measurement, "kg")


if __name__ == "__main__":
    unittest.main()
