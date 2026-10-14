"""Decode ProSOFT 10 alarm flags from BLE manufacturer data."""

from __future__ import annotations

from .const import MANUFACTURER_ID


def continuous_flow_alarm(manufacturer_data: dict[int, bytes]) -> bool | None:
    """Return the NF-02 water-leak flag, or None without a valid beacon."""
    data = manufacturer_data.get(MANUFACTURER_ID)
    if data is None or len(data) < 3:
        return None
    return bool(data[0] & 0x02)
