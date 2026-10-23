"""Constants for the Goodwe Modbus integration."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "goodwe_mb"
MANUFACTURER = "Goodwe"
ATTRIBUTION = "Data provided by the inverter via Modbus"
CONF_UNIT_ID = "unit_id"
CONF_POWER_SCAN_INTERVAL = "power_scan_interval"
SCAN_INTERVAL = 30
POWER_SCAN_INTERVAL = 10
PROTOCOLS = ["tcp", "serial"]
