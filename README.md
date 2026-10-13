# Aqua Danmark ProSOFT 10 for Home Assistant

Unofficial, read-only Bluetooth integration for the Aqua Danmark ProSOFT 10 water softener. It is based on the app protocol and real replies from one ProSOFT 10 device. Version 0.1.2 has been tested on one running Home Assistant installation with a Raspberry Pi Bluetooth adapter. Other devices and adapter setups may behave differently.

The integration reads the device over Bluetooth every five minutes. It does not change settings or start regeneration.

| Sensor | Source | Unit | Status |
|---|---|---|---|
| Remaining treated water | `1161` | L | Confirmed in Home Assistant |
| Salt remaining | `1006` | kg | Confirmed in Home Assistant; unit inferred from app display |
| Salt level | `1006 / 1004` | % | Confirmed in Home Assistant at 85%, matching the app |
| Total treated water | `1169` | m³ | Confirmed in Home Assistant and app formatting |
| Regeneration | `1174` | none / in progress / scheduled | Value `0` confirmed in Home Assistant; other mappings from app code |

Unavailable readings appear as unknown. The total-water sensor is a cumulative meter suitable for Home Assistant water statistics; its state may change only after the device increments a whole cubic metre.

## Requirements

- Home Assistant with a **connectable** Bluetooth adapter or Bluetooth proxy in range of the water softener.
- HACS installed in Home Assistant.
- The phone app must be disconnected while Home Assistant connects; many BLE devices allow only one client at a time.

## Install through HACS

1. In HACS, open the menu and select **Custom repositories**.
2. Add `https://github.com/mplys3/ha-prosoft10` as category **Integration**.
3. Find **Aqua Danmark ProSOFT 10** and install it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration** and search for **Aqua Danmark ProSOFT 10**. If the device is discovered automatically, confirm it. Otherwise, enter its Bluetooth address manually.

HACS checks the GitHub repository for later versions. Install updates from HACS and restart Home Assistant when prompted.

## Troubleshooting

- If setup says the device is out of range, make sure Home Assistant's Bluetooth adapter or proxy supports active connections and that the iPhone app is disconnected.
- If setup reports no available Bluetooth connection slot while advertisements are still visible, disconnect both the Aqua Danmark app and nRF Connect, wait briefly, and try again. The integration retries transient connection failures, but it cannot take over a connection held by another client or create an extra adapter slot.
- If manual setup is needed, use the Bluetooth address reported by Home Assistant's Bluetooth integration or a scanner near the Home Assistant host. iOS may show a different address because BLE devices can use private addresses.
- If only some values are unknown, the device may not support the corresponding parameter. The salt percentage requires both `1006` and `1004`.
- Enable debug logging for `custom_components.prosoft10` to see which parameter fails. Never share full debug logs without checking for identifiers.

## Protocol

The BLE characteristic is `0000abf1-0000-1000-8000-00805f9b34fb`. A read request such as `@1169\r\n` is written to that characteristic. The device answers by notification, for example `@116900053`, meaning 53 m³ of water treated in total. Responses observed so far do not require a terminating CR/LF. This repository contains an independent implementation; it does not include the vendor APK or decompiled vendor code.

## Feedback

Please open a [GitHub issue](https://github.com/mplys3/ha-prosoft10/issues) with your Home Assistant version, device model and relevant debug messages if a reading is missing or wrong. Avoid posting your Bluetooth address publicly.

This project is not affiliated with Aqua Danmark.
