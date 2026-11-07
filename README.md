# ControlMySpa for Home Assistant

Custom integration for **Balboa ControlMySpa** equipped hot tubs. It talks to the
ControlMySpa cloud API and exposes the spa as a proper Home Assistant device.

> Unofficial. Balboa does not publish or support this API; it is the same one the
> ControlMySpa mobile app uses. It can change without notice.

## Features

- **Climate** entity — current water temperature, target temperature, READY/REST heater mode
- **Switches** — every pump (jet), light and blower the controller reports
- **Binary sensors** — online, panel locked, priming mode, fault, ozone, filters, circulation pump
- **Sensors** — fault message, alert count, temperature range, heater mode, controller software, last gateway ping
- Cloud polling every 60 s (configurable), with automatic re-authentication

## Requirements

- A ControlMySpa account with at least one spa linked to it — the same account you
  use in the ControlMySpa mobile app

That's all. No API key, no developer account, and no device ID or CMS code to look up.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → *Custom repositories*
2. Add `https://github.com/halkosajtarevic/ha-controlmyspa` as type *Integration*
3. Install **ControlMySpa**, then restart Home Assistant

### Manual

Copy `custom_components/controlmyspa` into your `config/custom_components/` folder and
restart Home Assistant.

## Configuration

*Settings → Devices & services → Add integration → ControlMySpa*

1. Enter the email and password of your ControlMySpa account.
2. If the account owns more than one spa, tick the ones you want. Each selected spa
   becomes its own device, named after the spa's own name (or its serial number).
   Accounts with a single spa are configured in one step.

Re-authentication is handled automatically: if the password changes, Home Assistant
asks for the new one instead of failing.

## Entities

| Platform | Entity | Notes |
|---|---|---|
| `climate` | Spa | target temperature, READY/REST preset |
| `switch` | Pump 1…n | `jet` component, OFF/HIGH |
| `switch` | Light 1…n | `light` component |
| `switch` | Blower 1…n | only when the controller reports one |
| `binary_sensor` | Online, Panel locked, Priming, Fault active | |
| `binary_sensor` | Ozone, Filter 1…2, Circulation pump | read-only — the API cannot set these |
| `sensor` | Fault, Alerts, Temperature range, Heater mode, Controller software, Last gateway ping | |

## Good to know

- **Cloud only.** The gateway keeps its own MQTT/TLS session to Balboa; there is no
  local API to poll.
- **Temperatures are stored in Fahrenheit** in the cloud, and the `isCelsius` flag is
  not trustworthy: some gateways report Fahrenheit numbers with the flag set to
  Celsius. The integration therefore treats any reading above 45 as Fahrenheit, which
  is safely above any real spa temperature. Entities always expose Celsius and Home
  Assistant converts to your display unit.
- **Polling**, not push: the spa reports roughly once a minute, so a command can take
  one polling cycle to show up.
- Panel lock/prime/filter/ozone states are read-only in this integration.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.controlmyspa: debug
```

Download diagnostics from the integration page (credentials are redacted).

## License

MIT
