"""Number platform for Goodwe modbus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.components.number.const import NumberDeviceClass
from homeassistant.const import PERCENTAGE

from .entity import GoodweEntity, GoodweEntityDescription

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from goodwe_modbus.device import GoodweInverter
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import (
        GoodweConfigEntry,
    )


@dataclass(frozen=True, kw_only=True)
class GoodweNumberDescription(NumberEntityDescription, GoodweEntityDescription):
    """Describe a Goodwe sensor."""

    value_fn: Callable[[GoodweInverter], float | None]
    write_fn: Callable[[GoodweInverter, int], Awaitable[None]]


NUMBER_DESCRIPTIONS: tuple[GoodweNumberDescription, ...] = (
    GoodweNumberDescription(
        key="active power",
        component="powercontrol",
        translation_key="active_power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=PERCENTAGE,
        native_max_value=100,
        native_min_value=0,
        native_step=1,
        value_fn=lambda device: device.powercontrol.active_power_export_limit,
        write_fn=lambda device, value: (
            device.powercontrol.async_set_active_power_export_limit(int(value))
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GoodweConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    runtime_data = entry.runtime_data
    async_add_entities(
        GoodweNumber(
            runtime_data=runtime_data,
            entity_description=entity_description,
        )
        for entity_description in NUMBER_DESCRIPTIONS
    )


class GoodweNumber(GoodweEntity, NumberEntity):
    """Reports whether any fault in one subsystem is currently active."""

    entity_description: GoodweNumberDescription

    @property
    @override
    def native_value(self) -> int | float | None:
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.device
        )
        return self._attr_native_value

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the device."""
        await self.entity_description.write_fn(self.coordinator.device, int(value))
        await self.coordinator.async_request_refresh()
