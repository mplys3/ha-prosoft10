"""Manual history retrieval for ProSOFT 10."""

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProsoftCoordinator


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ProsoftFetchLog(coordinator, "706", "fetch_parameter_log"),
        ProsoftFetchLog(coordinator, "707", "fetch_event_log"),
    ])


class ProsoftFetchLog(CoordinatorEntity[ProsoftCoordinator], ButtonEntity):
    """Fetch a log over the serialized existing BLE session."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:download"

    def __init__(self, coordinator: ProsoftCoordinator, code: str, key: str) -> None:
        super().__init__(coordinator)
        self._code = code
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.address)})

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_read_parameter(self._code)
        except Exception as error:
            raise HomeAssistantError(f"Could not fetch ProSOFT log {self._code}: {type(error).__name__}: {error}") from error
