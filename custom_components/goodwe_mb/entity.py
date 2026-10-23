"""GoodweEntity base class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import GoodweDataUpdateCoordinator, GoodweRuntimeData


@dataclass(frozen=True, kw_only=True)
class GoodweEntityDescription(EntityDescription):
    """Describe a sensor backed by a device attribute."""

    component: str  # the name mentioned in the update report


class GoodweEntity(CoordinatorEntity[GoodweDataUpdateCoordinator]):
    """GoodweEntity class."""

    _attr_has_entity_name = True
    entity_description: GoodweEntityDescription
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        runtime_data: GoodweRuntimeData,
        entity_description: GoodweEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(runtime_data.coordinator_for(entity_description.component))
        self.entity_description = entity_description
        serial = (
            self.coordinator.device.identity.serial
            or self.coordinator.config_entry.unique_id
            or "unknown"
        )
        self._attr_unique_id = f"{serial}_{entity_description.key}"
        self._attr_device_info = self.coordinator.device_info

    @property
    @override
    def available(self) -> bool:
        """Whether this entity's component answered the most recent poll."""
        if not super().available or self.coordinator.data is None:
            return False
        return self.entity_description.component not in self.coordinator.data.failed
