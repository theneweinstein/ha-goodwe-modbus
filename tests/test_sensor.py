"""Tests for the Goodwe Modbus HA sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection.model import UpdateReport

from custom_components.goodwe_mb import async_setup_entry
from custom_components.goodwe_mb.const import (
    CONF_POWER_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DOMAIN,
    POWER_SCAN_INTERVAL,
    SCAN_INTERVAL,
)
from custom_components.goodwe_mb.coordinator import (
    GoodweDataUpdateCoordinator,
    GoodweRuntimeData,
)


@pytest.fixture(name="mock_device")
def _mock_device_fixture() -> MagicMock:
    """Return a mock GoodweInverter with controllable identity and state."""
    device = MagicMock()
    device.identity.serial = "SN1234567890"
    device.identity.type = "GW10K-ET"
    device.state.system_state = MagicMock()
    device.state.system_state.name = "NORMAL"
    device.state.generation_time_total = 123
    device.state.inverter_temperature = 22.5
    device.state.active_faults = frozenset()
    device.grid.voltage_l1 = 230.0
    device.grid.voltage_l2 = 231.0
    device.grid.voltage_l3 = 229.0
    device.grid.current_l1 = 5.0
    device.grid.current_l2 = 4.5
    device.grid.current_l3 = 4.8
    device.grid.power = 1500
    device.grid.power_l1 = 1150.0
    device.grid.power_l2 = 1039.5
    device.grid.power_l3 = 1099.2
    device.pv.strings = [
        MagicMock(pv_voltage=360.0, pv_current=3.5, pv_power=1260.0),
        MagicMock(pv_voltage=340.0, pv_current=3.0, pv_power=1020.0),
    ]
    device.energy.daily_energy = 5.0
    device.energy.lifetime_energy = 100.0
    device.powercontrol.active_power_export_limit = 75
    return device


async def _setup_entry(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """Set up a config entry with the given mock device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "10.0.0.234:502",
            CONF_PROTOCOL: "tcp",
            CONF_UNIT_ID: 246,
            CONF_SCAN_INTERVAL: SCAN_INTERVAL,
            CONF_POWER_SCAN_INTERVAL: POWER_SCAN_INTERVAL,
        },
        title="GW10K-ET",
        unique_id="SN1234567890",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.goodwe_mb.async_get_unit",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.goodwe_mb.GoodweInverter",
            return_value=mock_device,
        ),
        patch(
            "custom_components.goodwe_mb.GoodweDataUpdateCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.goodwe_mb.GoodweDataUpdateCoordinator.async_refresh",
            new_callable=AsyncMock,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


from homeassistant.config_entries import MockConfigEntry


async def test_power_sensor(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """The power sensor should read from grid.power."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_power")
    assert state is not None
    assert state.state == "1500"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"
    assert state.attributes["state_class"] == "measurement"


async def test_energy_today_sensor(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """The energy_today sensor should read from energy.daily_energy."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_energy_produced_today")
    assert state is not None
    assert state.state == "5.0"
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["state_class"] == "total_increasing"


async def test_energy_total_sensor(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """The energy_total sensor should read from energy.lifetime_energy."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_energy_produced_total")
    assert state is not None
    assert state.state == "100.0"
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_pv_voltage_string_1(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """PV voltage for string 1 should be available."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_voltage_string_1")
    assert state is not None
    assert state.state == "360.0"


async def test_pv_current_string_2(hass: HomeAssistant, mock_device: MagicMock) -> None:
    """PV current for string 2 should be available."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_current_string_2")
    assert state is not None
    assert state.state == "3.0"


async def test_inverter_temperature(
    hass: HomeAssistant, mock_device: MagicMock
) -> None:
    """Inverter temperature should be a diagnostic sensor."""
    await _setup_entry(hass, mock_device)

    state = hass.states.get("sensor.gw10k_et_inverter_temperature")
    assert state is not None
    assert state.state == "22.5"
    assert state.attributes.get("entity_category") == "diagnostic"
