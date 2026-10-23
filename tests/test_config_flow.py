"""Tests for the Goodwe Modbus HA component config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusError

from custom_components.goodwe_mb.const import (
    CONF_POWER_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DOMAIN,
    POWER_SCAN_INTERVAL,
    SCAN_INTERVAL,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from homeassistant.core import HomeAssistant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_device(
    serial: str = "SN1234567890", model: str = "GW10K-ET"
) -> MagicMock:
    """Build a mock GoodweInverter that returns known identity values."""
    device = MagicMock()
    device.identity.serial = serial
    device.identity.type = model
    device.async_update = AsyncMock()
    return device


@pytest.fixture(name="patch_probe")
async def _patch_probe() -> AsyncGenerator[MagicMock, Any]:
    """Patch _async_probe and GoodweInverter creation to return a mock device."""
    device = _make_mock_device()
    with (
        patch(
            "custom_components.goodwe_mb.config_flow.async_get_temporary_unit",
            new_callable=AsyncMock,
        ) as mock_get_unit,
        patch(
            "custom_components.goodwe_mb.config_flow.GoodweInverter",
            return_value=device,
        ),
    ):
        mock_unit = MagicMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_unit
        mock_get_unit.return_value = mock_cm
        yield mock_get_unit


async def _init_flow(
    hass: HomeAssistant,
    source: str,
    data: dict[str, Any],
    entry_id: str | None = None,
) -> dict[str, Any]:
    """Initiate a config flow with the given source and data."""
    context = {"source": source}
    if entry_id is not None:
        context["entry_id"] = entry_id
    return await hass.config_entries.flow.async_init(DOMAIN, context=context, data=data)


_DEFAULT_DATA: dict[str, Any] = {
    CONF_ADDRESS: "10.0.0.234:502",
    CONF_PROTOCOL: "tcp",
    CONF_UNIT_ID: 246,
    CONF_SCAN_INTERVAL: SCAN_INTERVAL,
    CONF_POWER_SCAN_INTERVAL: POWER_SCAN_INTERVAL,
}


# ---------------------------------------------------------------------------
# Config flow: async_step_user
# ---------------------------------------------------------------------------


async def test_user_step_create_entry(hass: HomeAssistant, patch_probe) -> None:
    """Successful user step creates a config entry."""
    result = await _init_flow(hass, config_entries.SOURCE_USER, _DEFAULT_DATA)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "GW10K-ET"
    assert result["data"][CONF_ADDRESS] == "10.0.0.234:502"
    assert result["data"][CONF_UNIT_ID] == 246


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    """Failed connection shows an error."""
    mock_device = MagicMock()
    mock_device.async_update = AsyncMock(side_effect=ModbusError("timeout"))

    with (
        patch(
            "custom_components.goodwe_mb.config_flow.async_get_temporary_unit",
            new_callable=AsyncMock,
        ) as mock_get_unit,
        patch(
            "custom_components.goodwe_mb.config_flow.GoodweInverter",
            return_value=mock_device,
        ),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = MagicMock()
        mock_get_unit.return_value = mock_cm
        result = await _init_flow(hass, config_entries.SOURCE_USER, _DEFAULT_DATA)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_step_duplicate(hass: HomeAssistant, patch_probe) -> None:
    """A second entry for the same serial should abort."""
    # First entry
    await _init_flow(hass, config_entries.SOURCE_USER, _DEFAULT_DATA)

    # Second entry with same serial
    result = await _init_flow(hass, config_entries.SOURCE_USER, _DEFAULT_DATA)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Config flow: async_step_reconfigure
# ---------------------------------------------------------------------------


async def test_reconfigure_success(
    hass: HomeAssistant, config_entry, patch_probe
) -> None:
    """Reconfigure with a working address should update the entry."""
    data = {**_DEFAULT_DATA, CONF_ADDRESS: "10.0.0.235:502"}
    result = await _init_flow(
        hass, config_entries.SOURCE_RECONFIGURE, data, config_entry.entry_id
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_serial_mismatch(hass: HomeAssistant, config_entry) -> None:
    """Reconfigure to a different inverter should abort with serial_mismatch."""
    different_device = _make_mock_device(serial="DIFFERENT_SERIAL")

    with (
        patch(
            "custom_components.goodwe_mb.config_flow.async_get_temporary_unit",
            new_callable=AsyncMock,
        ) as mock_get_unit,
        patch(
            "custom_components.goodwe_mb.config_flow.GoodweInverter",
            return_value=different_device,
        ),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = MagicMock()
        mock_get_unit.return_value = mock_cm
        result = await _init_flow(
            hass,
            config_entries.SOURCE_RECONFIGURE,
            {**_DEFAULT_DATA, CONF_ADDRESS: "10.0.0.236:502"},
            config_entry.entry_id,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "serial_mismatch"


async def test_reconfigure_cannot_connect(hass: HomeAssistant, config_entry) -> None:
    """Reconfigure to an unreachable address shows error."""
    mock_device = MagicMock()
    mock_device.async_update = AsyncMock(side_effect=ModbusError("timeout"))

    with (
        patch(
            "custom_components.goodwe_mb.config_flow.async_get_temporary_unit",
            new_callable=AsyncMock,
        ) as mock_get_unit,
        patch(
            "custom_components.goodwe_mb.config_flow.GoodweInverter",
            return_value=mock_device,
        ),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = MagicMock()
        mock_get_unit.return_value = mock_cm
        result = await _init_flow(
            hass,
            config_entries.SOURCE_RECONFIGURE,
            {**_DEFAULT_DATA, CONF_ADDRESS: "10.0.0.237:502"},
            config_entry.entry_id,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"
