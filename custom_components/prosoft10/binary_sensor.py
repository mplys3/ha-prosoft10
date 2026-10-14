"""ProSOFT 10 Bluetooth beacon alarms."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import ProsoftCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the continuous-flow alarm."""
    async_add_entities([ProsoftContinuousFlow(hass.data[DOMAIN][entry.entry_id])])


class ProsoftContinuousFlow(CoordinatorEntity[ProsoftCoordinator], BinarySensorEntity):
    """Water leak/continuous flow alarm from NF-02 advertisement flag."""

    _attr_has_entity_name = True
    _attr_translation_key = "continuous_flow"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:water-alert"

    def __init__(self, coordinator: ProsoftCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_continuous_flow"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=NAME,
            manufacturer="Aqua Danmark",
            model="ProSOFT 10",
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        )

    @property
    def available(self) -> bool:
        """Do not report a stale safe state when advertisements stop."""
        return self.coordinator.flow_alarm is not None

    @property
    def is_on(self) -> bool | None:
        """True when the device advertises continuous water flow."""
        return self.coordinator.flow_alarm
