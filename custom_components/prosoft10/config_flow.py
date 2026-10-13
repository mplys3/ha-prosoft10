"""Config flow for Aqua Danmark ProSOFT 10."""

from __future__ import annotations

import re

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import DOMAIN, NAME

_ADDRESS = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")


class ProsoftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up a ProSOFT device by Bluetooth address."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str = NAME

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Offer a device found by Home Assistant's Bluetooth scanner."""
        if not discovery_info.connectable:
            return self.async_abort(reason="not_connectable")
        address = discovery_info.address.upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        self._discovered_address = address
        self._discovered_name = discovery_info.name or NAME
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        """Ask the user to confirm a discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name,
                data={"address": self._discovered_address},
            )
        return self.async_show_form(step_id="confirm")

    async def async_step_user(self, user_input=None):
        """Allow manual setup if Bluetooth discovery misses the device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input["address"].strip().upper()
            if not _ADDRESS.fullmatch(address):
                errors["address"] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=NAME, data={"address": address})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("address"): str}),
            errors=errors,
        )
