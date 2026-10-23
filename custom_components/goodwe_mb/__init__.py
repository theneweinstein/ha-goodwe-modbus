"""
Custom integration to integrate Goodwe Modbus with Home Assistant.

For more details about this integration, please refer to
https://github.com/theneweinstein/ha-goodwe-modbus
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from goodwe_modbus.device import GoodweInverter
from homeassistant.components.modbus import async_get_unit
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .const import (
    CONF_POWER_SCAN_INTERVAL,
    CONF_UNIT_ID,
    POWER_SCAN_INTERVAL,
    SCAN_INTERVAL,
)
from .coordinator import (
    GoodweConfigEntry,
    GoodweDataUpdateCoordinator,
    GoodweRuntimeData,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoodweConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    if entry.data[CONF_PROTOCOL] == "serial":
        modbus_parameters = ModbusSerialParams(device=entry.data[CONF_ADDRESS])
    else:
        host, port = entry.data[CONF_ADDRESS].rsplit(":", 1)
        modbus_parameters = ModbusTcpParams(host=host, port=int(port))
    unit = async_get_unit(
        hass,
        entry,
        modbus_parameters,
        entry.data[CONF_UNIT_ID],
    )
    device = GoodweInverter(unit)
    scan_interval = timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL))
    readings = GoodweDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_readings,
        scan_interval,
    )
    settings = GoodweDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_settings,
        scan_interval,
    )
    # Fast grid coordinator for the power sensor.
    power_scan_interval = timedelta(
        seconds=entry.data.get(CONF_POWER_SCAN_INTERVAL, POWER_SCAN_INTERVAL)
    )
    grid_fast: GoodweDataUpdateCoordinator | None = None
    if power_scan_interval < scan_interval:
        grid_fast = GoodweDataUpdateCoordinator(
            hass,
            entry,
            device,
            device.async_update_grid,
            power_scan_interval,
        )
    try:
        await readings.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        # Inverter is offline (night, no solar). Set up the platform anyway
        # so the energy sensors stay available with their last restored values.
        # They will get live data once the inverter comes back online.
        _LOGGER.info(
            "%s: inverter is not answering, setting up without live data: %s",
            entry.title,
            readings.last_exception,
        )

        @callback
        def _async_reload_once_answered() -> None:
            """Reload the entry once the inverter answers."""
            if readings.last_update_success:
                hass.config_entries.async_schedule_reload(entry.entry_id)

        entry.async_on_unload(readings.async_add_listener(_async_reload_once_answered))
    else:
        await settings.async_refresh()
        if grid_fast is not None:
            await grid_fast.async_refresh()
    entry.runtime_data = GoodweRuntimeData(
        readings=readings,
        settings=settings,
        grid_fast=grid_fast,
        inverter_device_id=entry.data[CONF_UNIT_ID],
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: GoodweConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
