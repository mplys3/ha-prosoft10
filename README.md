# Aqua Danmark ProSOFT 10 for Home Assistant

Unofficial, read-only Bluetooth integration for the Aqua Danmark ProSOFT 10 water softener. It is based on the app protocol and real replies from one ProSOFT 10 device. The original five sensors were confirmed on a running Home Assistant installation; the new alarm and regeneration-time sensors in version 0.3.0 still need device testing. Other devices and adapter setups may behave differently.

The integration reads the device over Bluetooth every 20 seconds, matching the dashboard polling interval found in the vendor app. It keeps one BLE connection open between polls, reconnects if the device drops that connection, and disconnects when the integration is unloaded. It does not change settings or start regeneration.

| Sensor | Source | Unit | Status |
|---|---|---|---|
| Remaining treated water | `1161` | L | Confirmed in Home Assistant |
| Salt remaining | `1006` | kg | Confirmed in Home Assistant; unit inferred from app display |
| Salt level | `1006 / 1004` | % | Confirmed in Home Assistant at 85%, matching the app |
| Salt per regeneration (raw value) | `1005` | unverified | Device returned `1.25`; this must not be interpreted as 1.25 kg without calibration |
| Total treated water | `1169` | m³ | Confirmed in Home Assistant and app formatting |
| Regeneration | `1174` | none / in progress / scheduled | Value `0` confirmed in Home Assistant; other mappings from app code |
| Regeneration time 1–4 | `1017`–`1020` | local time | Four configured start times from app protocol; `99:99` means disabled; device values not yet verified |
| Continuous water flow | NF-02 bit in BLE manufacturer data | alarm on / off | Decoded from Android app; live HA behavior not yet verified |

Unavailable readings appear as unknown. The total-water sensor is a cumulative meter suitable for Home Assistant water statistics; its state may change only after the device increments a whole cubic metre.

The four regeneration times are configured opportunities for regeneration, **not a promised date and time for the next run**. Capacity and operating rules may determine whether a regeneration is actually scheduled. Disabled time slots show as unknown. Parameter `1005` is read together with these settings at startup and approximately every five minutes. Its `raw_value` attribute retains the response body. The observed value `1.25` exceeds [Aqua Danmark's published maximum of 0.63 kg per regeneration for ProSOFT 10](https://aquadanmark.dk/prosoft-10) if treated as kilograms. The unit or conversion of parameter `1005` is therefore unverified; the integration shows it without a unit until confirmed.

The continuous-flow binary sensor follows the device's NF-02 alarm bit in Bluetooth advertisements. It becomes unavailable if no valid advertisement has been received for five minutes, rather than continuing to show an old safe state. Some devices stop advertising while a BLE client is connected; if that happens with this device, the alarm will remain unavailable while the integration's persistent connection is open. Do not rely on this experimental entity as the sole leak alarm until its behavior is verified on your device.

## Requirements

- Home Assistant with a **connectable** Bluetooth adapter or Bluetooth proxy in range of the water softener.
- HACS installed in Home Assistant.
- The phone app must be disconnected while Home Assistant is using the device; many BLE devices allow only one client at a time. Disable the integration temporarily in Home Assistant to use the phone app.

## Install through HACS

1. In HACS, open the menu and select **Custom repositories**.
2. Add `https://github.com/mplys3/ha-prosoft10` as category **Integration**.
3. Find **Aqua Danmark ProSOFT 10** and install it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration** and search for **Aqua Danmark ProSOFT 10**. If the device is discovered automatically, confirm it. Otherwise, enter its Bluetooth address manually.

HACS checks the GitHub repository for later versions. Install updates from HACS and restart Home Assistant when prompted.

## Read a parameter on demand

In Home Assistant, open **Developer Tools → Actions**, select **Aqua Danmark ProSOFT 10: Read parameter** (`prosoft10.read_parameter`), and enter:

```yaml
code: "1146"
```

Run the action to see the raw value in its response. If you have configured multiple ProSOFT 10 devices, include their `address` as well. This uses the same existing Bluetooth connection as the sensors, so a poll and a manual read cannot collide. The value is not saved as a sensor. Parameter `1146` is labelled as an advanced-settings code in the app; its returned value may be sensitive, so check it before sharing an action response or automation trace. The action sends only a read request and cannot change a setting.

## Troubleshooting

- If setup says the device is out of range, make sure Home Assistant's Bluetooth adapter or proxy supports active connections and that the iPhone app is disconnected.
- If setup reports a Bluetooth connection error, read the full error detail: a device seen earlier may no longer be visible to a connectable scanner, even when Home Assistant has free connection slots. Check the Bluetooth Advertisement Monitor for a current advertisement from the device. If the phone app is connected, disconnect it before Home Assistant tries again.
- If manual setup is needed, use the Bluetooth address reported by Home Assistant's Bluetooth integration or a scanner near the Home Assistant host. iOS may show a different address because BLE devices can use private addresses.
- If only some values are unknown, the device may not support the corresponding parameter. The salt percentage requires both `1006` and `1004`.
- Enable debug logging for `custom_components.prosoft10` to see which parameter fails. Never share full debug logs without checking for identifiers.

## Protocol

The BLE characteristic is `0000abf1-0000-1000-8000-00805f9b34fb`. A read request such as `@1169\r\n` is written to that characteristic. The device answers by notification, for example `@116900053`, meaning 53 m³ of water treated in total. Responses observed so far do not require a terminating CR/LF. This repository contains an independent implementation; it does not include the vendor APK or decompiled vendor code.

## Feedback

Please open a [GitHub issue](https://github.com/mplys3/ha-prosoft10/issues) with your Home Assistant version, device model and relevant debug messages if a reading is missing or wrong. Avoid posting your Bluetooth address publicly.

This project is not affiliated with Aqua Danmark.
