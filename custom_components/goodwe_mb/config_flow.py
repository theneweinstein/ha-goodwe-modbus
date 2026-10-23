"""Adds config flow for Blueprint."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from goodwe_modbus.device import GoodweInverter
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL
from modbus_connection import ModbusError, ModbusSerialParams, ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN, STEP_USER_DATA_SCHEMA

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
            data_schema=STEP_USER_DATA_SCHEMA,  # type: ignore[arg-type]
            errors=errors,
        )
