"""Config flow for the Goodwe Modbus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from goodwe_modbus.device import GoodweInverter
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL, CONF_SCAN_INTERVAL
from modbus_connection import ModbusError, ModbusSerialParams, ModbusTcpParams
from probatio import In, Optional, Required, Schema

from .const import (
    CONF_POWER_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DOMAIN,
    POWER_SCAN_INTERVAL,
    PROTOCOLS,
    SCAN_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def _async_probe(
    hass: HomeAssistant, address: str, protocol: str, unit_id: int
) -> tuple[str, str]:
    """Return the device's serial and model, or raise ModbusError if unreachable."""
    if protocol == "serial":
        modbus_parameters = ModbusSerialParams(device=address)
    else:
        host, port = address.rsplit(":", 1)
        modbus_parameters = ModbusTcpParams(host=host, port=int(port))
    async with async_get_temporary_unit(hass, modbus_parameters, unit_id) as unit:
        device = GoodweInverter(unit)
        await device.async_update()
        return str(device.identity.serial), str(device.identity.type)


class GoodweModbusFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Goodwe Modbus."""

    @staticmethod
    def _build_schema(
        defaults: dict[str, Any] | None = None,
    ) -> Schema:
        """Build the connection-data schema, optionally with defaults."""
        return Schema(
            {
                Required(
                    CONF_ADDRESS,
                    default=defaults.get(CONF_ADDRESS) if defaults else None,
                ): str,
                Required(
                    CONF_PROTOCOL,
                    default=defaults.get(CONF_PROTOCOL) if defaults else None,
                ): In(PROTOCOLS),
                Required(
                    CONF_UNIT_ID,
                    default=defaults.get(CONF_UNIT_ID) if defaults else None,
                ): int,
                Optional(
                    CONF_SCAN_INTERVAL,
                    default=defaults.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)
                    if defaults
                    else SCAN_INTERVAL,
                ): int,
                Optional(
                    CONF_POWER_SCAN_INTERVAL,
                    default=defaults.get(CONF_POWER_SCAN_INTERVAL, POWER_SCAN_INTERVAL)
                    if defaults
                    else POWER_SCAN_INTERVAL,
                ): int,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                serial, model = await _async_probe(
                    self.hass,
                    user_input[CONF_ADDRESS],
                    user_input[CONF_PROTOCOL],
                    user_input[CONF_UNIT_ID],
                )
            except ModbusError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=model, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),  # type: ignore[arg-type]
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                serial, model = await _async_probe(
                    self.hass,
                    user_input[CONF_ADDRESS],
                    user_input[CONF_PROTOCOL],
                    user_input[CONF_UNIT_ID],
                )
            except ModbusError:
                errors["base"] = "cannot_connect"
            else:
                # Verify the probed serial matches the existing unique id.
                if serial != entry.unique_id:
                    errors["base"] = "serial_mismatch"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates=user_input,
                        title=model,
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._build_schema(entry.data),  # type: ignore[arg-type]
            errors=errors,
            description_placeholders={
                "model": entry.title,
                "serial": entry.unique_id or "unknown",
            },
        )
