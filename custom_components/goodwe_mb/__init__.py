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
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusSerialParams, ModbusTcpParams, ModbusTimeoutError

from .const import CONF_UNIT_ID, SCAN_INTERVAL
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
    readings = GoodweDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_readings,
        timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)),
    )
    settings = GoodweDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_settings,
        timedelta(seconds=entry.data.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)),
    )
    try:
        await readings.async_config_entry_first_refresh()
    except Exception as err:
        failure = readings.last_exception
        if not (
            isinstance(failure, UpdateFailed)
            and isinstance(failure.__cause__, ModbusTimeoutError)
        ):
            raise
        _LOGGER.info(
            "%s: inverter is not answering, setting up without it: %s",
            entry.title,
            err,
        )

        @callback
        def _async_reload_once_answered() -> None:
            """Set up again in full once the inverter answers."""
            if readings.last_update_success:
                hass.config_entries.async_schedule_reload(entry.entry_id)

        entry.async_on_unload(readings.async_add_listener(_async_reload_once_answered))
    else:
        await settings.async_refresh()
    entry.runtime_data = GoodweRuntimeData(
        readings=readings,
        settings=settings,
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
