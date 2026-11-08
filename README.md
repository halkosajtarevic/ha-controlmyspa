<p align="center">
  <img src="https://raw.githubusercontent.com/halkosajtarevic/ha-controlmyspa/main/custom_components/controlmyspa/brand/icon.png" width="120" alt="ControlMySpa">
</p>

<h1 align="center">ControlMySpa for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/halkosajtarevic/ha-controlmyspa/releases"><img src="https://img.shields.io/github/v/release/halkosajtarevic/ha-controlmyspa?style=flat-square" alt="Release"></a>
  <a href="https://github.com/halkosajtarevic/ha-controlmyspa/blob/main/LICENSE"><img src="https://img.shields.io/github/license/halkosajtarevic/ha-controlmyspa?style=flat-square" alt="License"></a>
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square" alt="HACS"></a>
</p>

<p align="center">
  Bring your Balboa <b>ControlMySpa</b> hot tub into Home Assistant — temperatures, pumps,
  lights and faults as real entities, without soldering anything.
</p>

---

## Why this exists

Balboa's ControlMySpa cloud already knows everything about your spa — it just keeps it in
an app. This integration reads the same API the app uses and turns it into a proper Home
Assistant device, so your spa shows up in dashboards, automations and history like any
other appliance.

Sign in with your ControlMySpa account and pick your spa from a list. **No API key, no
developer account, no device ID or CMS code to hunt down.**

## Features

| | |
|---|---|
| 🌡️ **Climate** | Current water temperature, target temperature, `ready` / `rest` heater mode |
| 💧 **Pumps & blowers** | Every pump and blower the controller reports, as switches |
| 💡 **Lights** | On/off, including multi-zone controllers |
| 🚨 **Health** | Fault message, alert count, priming mode, panel lock, online state |
| 🔍 **Diagnostics** | Downloadable diagnostics with credentials redacted |
| 🔁 **Re-authentication** | Password changed? Home Assistant asks for the new one instead of breaking |

Read-only extras (ozone generator, filter cycles, circulation pump) are exposed as binary
sensors — the cloud API does not allow switching those.

## Installation

### HACS (recommended)

1. Install [HACS](https://hacs.xyz) if you haven't already
2. HACS → **Integrations** → ⋮ → **Custom repositories**
3. Add `https://github.com/halkosajtarevic/ha-controlmyspa` as type **Integration**
4. Install **ControlMySpa** and restart Home Assistant

### Manual

Copy `custom_components/controlmyspa/` into your `config/custom_components/` directory and
restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → ControlMySpa**

1. Enter the email and password of your ControlMySpa account.
2. If the account owns more than one spa, tick the ones you want. Each selected spa becomes
   its own device, named after the spa's own name (or its serial number). Accounts with a
   single spa are configured in one step.

Polling interval defaults to 60 seconds and can be changed under the integration's
**Configure** button.

## Entities

Per spa, you get:

| Platform | Entities |
|---|---|
| `climate` | Target temperature, current temperature, `ready`/`rest` preset |
| `switch` | Pump 1…n, Light 1…n, Blower 1…n |
| `binary_sensor` | Online, Panel locked, Priming mode, Fault active, Ozone, Filter 1…2, Circulation pump |
| `sensor` | Fault message, Alerts, Temperature range, Heater mode, Controller software, Last gateway ping |

## Automation examples

Keep the spa at temperature only when electricity is cheap:

```yaml
automation:
  - alias: "Spa: rest mode overnight"
    triggers:
      - trigger: time
        at: "23:00:00"
    actions:
      - action: climate.set_preset_mode
        target:
          entity_id: climate.spa
        data:
          preset_mode: rest

  - alias: "Spa: ready again in the morning"
    triggers:
      - trigger: time
        at: "06:00:00"
    actions:
      - action: climate.set_preset_mode
        target:
          entity_id: climate.spa
        data:
          preset_mode: ready
```

Notify when the spa reports a fault:

```yaml
automation:
  - alias: "Spa fault alert"
    triggers:
      - trigger: state
        entity_id: binary_sensor.spa_fault_active
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: "Spa reports: {{ state_attr('sensor.spa_fault', 'fault') or 'see app' }}"
```

## Good to know

- **Cloud only.** The gateway holds its own encrypted session to Balboa's broker; there is
  no local API to poll. If the internet or Balboa's cloud is down, the spa still runs — you
  just can't control it remotely. For offline control you need an RS-485 tap on the spa bus.
- **Instant feedback.** A command is acknowledged by the cloud in well under a second, but the
  spa reports the result on its next telemetry. The integration shows the requested state
  immediately and then polls every 2 s (max 30 s) until the spa confirms it, so switches stop
  snapping back and the new state appears within seconds instead of a polling cycle.
- **Polling, not push.** The gateway reports roughly once a minute, so a command can take a
  polling cycle to show up in Home Assistant.
- **Temperatures are stored in Fahrenheit** in the cloud, and the `isCelsius` flag cannot be
  trusted — some gateways report Fahrenheit numbers with the flag set to Celsius. Anything
  above 45 is treated as Fahrenheit, which is safely above any real water temperature.
  Entities expose Celsius; Home Assistant converts to your display unit.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.controlmyspa: debug
```

If something looks wrong, download **diagnostics** from the integration page — the spa
payload is included, credentials are redacted.

## Disclaimer

This is an unofficial integration. Balboa does not publish or support this API; it is the
same one the ControlMySpa mobile app uses, and it can change without notice. Use at your own
risk — nothing here is able to damage your spa, but automation mistakes can, so test
automations before letting them run unattended.

## Credits

- [`arska/controlmyspa`](https://github.com/arska/controlmyspa) — the Python client that
  documented the cloud API this integration is built on
- The Home Assistant community, for the conventions this follows

## License

MIT — see [LICENSE](LICENSE).
