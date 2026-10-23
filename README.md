# Goodwe Modbus

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Home Assistant][hass-shield]][hass]

_Home Assistant custom integration for Goodwe inverters over Modbus._

Communicates with a Goodwe inverter via Modbus TCP or serial (including serial-over-TCP) to read sensor data, monitor faults, and adjust the active power export limit.

## Supported features

- **Sensors**: Grid voltages (L1-L3), currents (L1-L3), frequencies (L1-L3), power, PV string voltage/current/power, inverter temperature, generation time, daily and lifetime energy.
- **Binary sensors**: Fault monitoring per subsystem (grid, PV, fan, thermal, communication, etc.).
- **Controls**: Active power export limit (0-100 %).
- **Diagnostics**: Raw Modbus register dump in the HA diagnostics download.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to "Integrations" --> "Custom repositories".
3. Add `https://github.com/theneweinstein/ha-goodwe-modbus` as an integration repository.
4. Click "Download" on the Goodwe Modbus integration.
5. Restart Home Assistant.

### Manual

Copy the `custom_components/goodwe_mb/` directory into your Home Assistant `custom_components/` directory and restart.

## Configuration

This integration is configured entirely through the Home Assistant UI.

1. Go to **Settings > Devices & services > Add integration**.
2. Search for "Goodwe Inverter Modbus".
3. Enter the connection details:
   - **Address**: IP address and port (e.g. `10.0.0.234:502`) or serial device path (e.g. `socket://10.0.0.234:502`).
   - **Protocol**: `tcp` (Modbus TCP) or `serial` (RS-485 / serial over TCP).
   - **Unit ID**: The Modbus unit ID of your inverter (commonly 1, 246, or 247).
   - **Scan interval**: How often to poll (default 30 seconds).

### Prerequisites

- A Modbus gateway or serial-to-Ethernet adapter connected to your Goodwe inverter.
- The Home Assistant built-in [Modbus integration](https://www.home-assistant.io/integrations/modbus/) must be loaded (it is listed as a dependency and loads automatically).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Library

This integration relies on the [goodwe-modbus](https://github.com/theneweinstein/goodwe_modbus) Python library, which handles the Modbus register map.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/theneweinstein/ha-goodwe-modbus.svg
[commits]: https://github.com/theneweinstein/ha-goodwe-modbus/commits/main
[hass-shield]: https://img.shields.io/badge/Home%20Assistant-2026.9-%2341BDF5.svg
[hass]: https://home-assistant.io/
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs]: https://github.com/hacs/integration
[license-shield]: https://img.shields.io/github/license/theneweinstein/ha-goodwe-modbus.svg
[releases-shield]: https://img.shields.io/github/release/theneweinstein/ha-goodwe-modbus.svg
[releases]: https://github.com/theneweinstein/ha-goodwe-modbus/releases
