"""Read-only sensors for ProSOFT 10."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    NAME,
    REGENERATION_STATE,
    REGENERATION_TIMES,
    SALT_CAPACITY,
    SALT_PER_REGENERATION,
    SALT_REMAINING,
    TOTAL_TREATED_WATER,
    WATER_REMAINING,
)
from .coordinator import ProsoftCoordinator
from .protocol import parse_regeneration_time


def _number(value: str | None) -> int | float | None:
    if value is None:
        return None
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return int(number) if number == int(number) else float(number)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one entity for each known read-only field."""
    coordinator: ProsoftCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ProsoftWaterRemaining(coordinator),
            ProsoftSaltRemaining(coordinator),
            ProsoftSaltPercent(coordinator),
            ProsoftSaltPerRegeneration(coordinator),
            ProsoftTotalWater(coordinator),
            ProsoftRegeneration(coordinator),
            *(
                ProsoftRegenerationTime(coordinator, index, code)
                for index, code in enumerate(REGENERATION_TIMES, 1)
            ),
        ]
    )


class ProsoftSensor(CoordinatorEntity[ProsoftCoordinator], SensorEntity):
    """Base sensor bound to one ProSOFT 10 device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ProsoftCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=NAME,
            manufacturer="Aqua Danmark",
            model="ProSOFT 10",
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        )


class ProsoftWaterRemaining(ProsoftSensor):
    """Remaining treatable water capacity."""

    _attr_translation_key = "water_remaining"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "water_remaining")

    @property
    def native_value(self) -> int | float | None:
        return _number(self.coordinator.data.get(WATER_REMAINING))


class ProsoftSaltRemaining(ProsoftSensor):
    """Remaining salt in kilograms."""

    _attr_translation_key = "salt_remaining"
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "salt_remaining")

    @property
    def native_value(self) -> int | float | None:
        return _number(self.coordinator.data.get(SALT_REMAINING))


class ProsoftSaltPercent(ProsoftSensor):
    """Salt level calculated from remaining and total salt capacity."""

    _attr_translation_key = "salt_level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:shaker"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "salt_level")

    @property
    def native_value(self) -> int | float | None:
        remaining = _number(self.coordinator.data.get(SALT_REMAINING))
        capacity = _number(self.coordinator.data.get(SALT_CAPACITY))
        if remaining is None or capacity is None or capacity <= 0:
            return None
        return round(remaining / capacity * 100)


class ProsoftSaltPerRegeneration(ProsoftSensor):
    """Unscaled parameter 1005; its physical unit is not yet verified."""

    _attr_translation_key = "salt_per_regeneration"
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "salt_per_regeneration")

    @property
    def native_value(self) -> int | float | None:
        return _number(self.coordinator.data.get(SALT_PER_REGENERATION))

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {"raw_value": self.coordinator.data.get(SALT_PER_REGENERATION)}


class ProsoftTotalWater(ProsoftSensor):
    """Cumulative treated water, measured in cubic metres."""

    _attr_translation_key = "total_treated_water"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.WATER
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "total_treated_water")

    @property
    def native_value(self) -> int | float | None:
        return _number(self.coordinator.data.get(TOTAL_TREATED_WATER))


class ProsoftRegeneration(ProsoftSensor):
    """Current regeneration status."""

    _attr_translation_key = "regeneration"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = ["none", "in_progress", "scheduled", "unknown"]
    _attr_icon = "mdi:autorenew"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator, "regeneration")

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(REGENERATION_STATE)
        if raw is None:
            return None
        return {"0": "none", "1": "in_progress", "2": "scheduled"}.get(
            raw.strip(), "unknown"
        )


class ProsoftRegenerationTime(ProsoftSensor):
    """One configured regeneration time, not a predicted next run."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: ProsoftCoordinator, index: int, code: str) -> None:
        super().__init__(coordinator, f"regeneration_time_{index}")
        self._attr_translation_key = f"regeneration_time_{index}"
        self._code = code

    @property
    def native_value(self) -> str | None:
        value = parse_regeneration_time(self.coordinator.data.get(self._code))
        return value.strftime("%H:%M") if value is not None else None
