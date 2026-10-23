"""Binary sensor platform for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from goodwe_modbus.faults import FaultCategory
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import EntityCategory

from .entity import GoodweEntity, GoodweEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import GoodweConfigEntry


@dataclass(frozen=True, kw_only=True)
class GoodweFaultBinarySensorDescription(
    GoodweEntityDescription, BinarySensorEntityDescription
):
    """Describe a Sofar fault-category binary sensor."""

    category: FaultCategory


FAULT_SENSOR_DESCRIPTIONS: tuple[GoodweFaultBinarySensorDescription, ...] = tuple(
    GoodweFaultBinarySensorDescription(
        key=f"fault_{category.value}",
        component="state",
        translation_key=f"fault_{category.value}",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        category=category,
    )
    for category in FaultCategory
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: GoodweConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    runtime_data = entry.runtime_data
    async_add_entities(
        GoodweFaultBinarySensor(
            runtime_data=runtime_data,
            entity_description=entity_description,
        )
        for entity_description in FAULT_SENSOR_DESCRIPTIONS
    )


class GoodweFaultBinarySensor(GoodweEntity, BinarySensorEntity):
    """Reports whether any fault in one subsystem is currently active."""

    entity_description: GoodweFaultBinarySensorDescription

    @property
    @override
    def is_on(self) -> bool:
        return any(
            fault.category is self.entity_description.category
            for fault in self.coordinator.device.state.active_faults
        )
