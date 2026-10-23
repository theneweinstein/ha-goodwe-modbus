"""Diagnostics platform for the Goodwe Modbus integration.

Provides config-entry diagnostics including decoded data, raw Modbus
register dumps, coordinator state, and active faults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .coordinator import GoodweDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .coordinator import GoodweConfigEntry

# Keys whose values are redacted in diagnostics output.
_TO_REDACT = {"serial", "address", "unit_id"}


def _component_data(
    coordinator: GoodweDataUpdateCoordinator,
) -> dict[str, Any]:
    """Collect the decoded data of every component attribute."""
    data: dict[str, Any] = {}
    device = coordinator.device

    # Serial number and model are always useful in diagnostics.
    try:
        data["identity"] = {
            "serial": device.identity.serial,
            "type": device.identity.type,
        }
    except Exception:  # noqa: BLE001
        pass

    # State (system state, temperature, faults, generation time)
    try:
        state = device.state
        data["state"] = {
            "system_state": str(state.system_state),
            "generation_time_total": state.generation_time_total,
            "inverter_temperature": state.inverter_temperature,
            "active_faults": [
                {"id": f.id, "key": f.key, "category": str(f.category)}
                for f in state.active_faults
            ],
        }
    except Exception:  # noqa: BLE001
        pass

    # Grid output (voltages, currents, frequencies, power)
    try:
        grid = device.grid
        data["grid"] = {
            "voltage_l1": grid.voltage_l1,
            "voltage_l2": grid.voltage_l2,
            "voltage_l3": grid.voltage_l3,
            "current_l1": grid.current_l1,
            "current_l2": grid.current_l2,
            "current_l3": grid.current_l3,
            "frequency_l1": grid.frequency_l1,
            "frequency_l2": grid.frequency_l2,
            "frequency_l3": grid.frequency_l3,
            "power": grid.power,
            "power_l1": grid.power_l1,
            "power_l2": grid.power_l2,
            "power_l3": grid.power_l3,
        }
    except Exception:  # noqa: BLE001
        pass

    # PV strings
    try:
        data["pv"] = [
            {
                "pv_voltage": s.pv_voltage,
                "pv_current": s.pv_current,
                "pv_power": s.pv_power,
            }
            for s in device.pv.strings
        ]
    except Exception:  # noqa: BLE001
        pass

    # Energy totals
    try:
        data["energy"] = {
            "daily_energy": device.energy.daily_energy,
            "lifetime_energy": device.energy.lifetime_energy,
        }
    except Exception:  # noqa: BLE001
        pass

    # Settings
    try:
        data["powercontrol"] = {
            "active_power_export_limit": device.powercontrol.active_power_export_limit,
        }
    except Exception:  # noqa: BLE001
        pass

    return data


async def _raw_registers(
    coordinator: GoodweDataUpdateCoordinator,
) -> dict[str, dict[str, int]]:
    """Read every inverter register as raw address-value pairs."""
    try:
        raw = await coordinator.device.async_read_raw()
    except Exception:  # noqa: BLE001
        return {}
    return {
        space: {str(address): value for address, value in registers.items()}
        for space, registers in raw.items()
    }


def _coordinator_state(
    coordinator: GoodweDataUpdateCoordinator,
) -> dict[str, Any]:
    """Diagnostic data about the coordinator itself."""
    return {
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: GoodweConfigEntry,
) -> Mapping[str, Any]:
    """Return diagnostics for a Goodwe Modbus config entry."""
    runtime_data = config_entry.runtime_data
    readings = runtime_data.readings
    settings = runtime_data.settings

    # Gather decoded data from all components.
    data = _component_data(readings)
    settings_data = _component_data(settings)

    # Attempt to fetch raw registers.
    raw = await _raw_registers(readings)

    # Look up the device registry entry.
    serial = readings.device.identity.serial
    device = None
    if serial is not None:
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_device(
            identifiers={(config_entry.domain, str(serial))}
        )

    payload: dict[str, Any] = {
        "entry": async_redact_data(config_entry.data, _TO_REDACT),
        "device_info": async_redact_data(
            {
                "serial_number": str(serial),
                "model": readings.device.identity.type,
            },
            _TO_REDACT,
        ),
        "readings_coordinator": _coordinator_state(readings),
        "settings_coordinator": _coordinator_state(settings),
        "data": data,
        "settings_data": settings_data,
        "raw_registers": raw,
    }

    if device is not None:
        payload["device_registry_entry"] = dr.async_entry_as_dict(device)

    return payload
