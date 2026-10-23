"""Shared fixtures for Goodwe HA component tests."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import MockConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL, CONF_SCAN_INTERVAL

from custom_components.goodwe_mb.const import (
    CONF_POWER_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DOMAIN,
    POWER_SCAN_INTERVAL,
    SCAN_INTERVAL,
)


@pytest.fixture(name="config_entry")
async def _config_entry_fixture(hass) -> MockConfigEntry:
    """Create and register a mock config entry."""
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
    return entry
