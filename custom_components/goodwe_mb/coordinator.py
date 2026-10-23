"""DataUpdateCoordinator for the Goodwe Modbus integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from goodwe_modbus.device import READINGS, SETTINGS
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTimeoutError
from modbus_connection.model import UpdateReport
from propcache.api import cached_property

from goodwe_mb.const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import timedelta

    from goodwe_modbus.device import GoodweInverter
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class GoodweDataUpdateCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Class to manage fetching data from the API."""

    config_entry: GoodweConfigEntry
    device: GoodweInverter
    _failed: frozenset[str] = frozenset()
    _inverter_offline: bool = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoodweConfigEntry,
        device: GoodweInverter,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=interval,
        )
        self.device = device
        self._poll = poll

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            report = await self._poll()
        except ModbusTimeoutError:
            # Inverter is offline (night time, no solar). Keep the last data
            # so entities remain available with their last known values and
            # no error is logged by the coordinator framework.
            if not self._inverter_offline:
                _LOGGER.warning(
                    "%s: inverter is not answering (timeout), "
                    "keeping last known values",
                    self.config_entry.title,
                )
                self._inverter_offline = True
            return self.data
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err

        self._inverter_offline = False

        if not report.updated:
            errors = list(report.failed.values())
            msg = f"no sub-system answered: {errors[0]}"
            raise UpdateFailed(msg) from ExceptionGroup(
                "every sub-system failed", errors
            )

        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning("Failed to fetch %s: %s", name, report.failed[name])
        self._failed = frozenset(report.failed)
        return report

    @cached_property
    def device_info(self) -> dr.DeviceInfo:
        """Describe the device to the registry."""
        serial = self.device.identity.serial or self.config_entry.unique_id
        model = self.device.identity.type or self.config_entry.title
        return dr.DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            manufacturer=MANUFACTURER,
            model=model,
            serial_number=str(serial),
        )


@dataclass
class GoodweRuntimeData:
    """Data for the Goodwe integration."""

    readings: GoodweDataUpdateCoordinator
    settings: GoodweDataUpdateCoordinator
    grid_fast: GoodweDataUpdateCoordinator | None
    inverter_device_id: str

    def coordinator_for(self, component: str) -> GoodweDataUpdateCoordinator:
        """Return the coordinator for a given component."""
        if component == "grid_fast":
            return self.grid_fast or self.readings
        if component in READINGS:
            return self.readings
        if component in SETTINGS:
            return self.settings
        msg = f"Unknown component {component}"
        raise ValueError(msg)


type GoodweConfigEntry = ConfigEntry[GoodweRuntimeData]
