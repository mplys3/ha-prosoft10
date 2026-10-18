"""Aqua Danmark ProSOFT 10 integration."""

import asyncio

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN
from .coordinator import ProsoftCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register a read-only action for one-off device parameters."""
    hass.data.setdefault(DOMAIN, {})

    async def async_read_parameter(call: ServiceCall) -> dict[str, str]:
        code = call.data["code"]
        address = call.data.get("address")
        coordinators = list(hass.data[DOMAIN].values())
        if address is not None:
            coordinators = [
                coordinator
                for coordinator in coordinators
                if coordinator.address.upper() == address.upper()
            ]
        if not coordinators:
            raise ServiceValidationError("No matching ProSOFT 10 device is configured")
        if len(coordinators) > 1:
            raise ServiceValidationError(
                "More than one ProSOFT 10 device is configured; supply its address"
            )

        try:
            value = await coordinators[0].async_read_parameter(code)
        except Exception as error:
            raise HomeAssistantError(
                f"Could not read ProSOFT 10 parameter {code}: {error}"
            ) from error
        return {"code": code, "value": value}

    hass.services.async_register(
        DOMAIN,
        "read_parameter",
        async_read_parameter,
        schema=vol.Schema(
            {
                vol.Required("code"): vol.All(
                    vol.Coerce(str), vol.Match(r"^[0-9]{4}$")
                ),
                vol.Optional("address"): str,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the BLE device and its sensors."""
    coordinator = ProsoftCoordinator(hass, entry)

    async def async_stop(_event) -> None:
        await coordinator.async_close()

    cancel_stop = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop)
    entry.async_on_unload(cancel_stop)
    try:
        coordinator.start_advertisements()
        await coordinator.async_config_entry_first_refresh()
    except (Exception, asyncio.CancelledError):
        cancel_stop()
        await coordinator.async_close()
        raise
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the sensors."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close()
        return True
    return False
