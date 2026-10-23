"""Sensor platform for Goodwe modbus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import IntEnum
from typing import TYPE_CHECKING, cast, override

from goodwe_modbus.enums import SystemState
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .entity import GoodweEntity, GoodweEntityDescription

if TYPE_CHECKING:
    from collections.abc import Callable

    from goodwe_modbus.device import GoodweInverter
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import (
        GoodweConfigEntry,
    )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GoodweConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    runtime_data = entry.runtime_data

    async_add_entities(
        _sensor_class(description)(runtime_data, description)
        for description in SENSOR_DESCRIPTIONS
    )


def _sensor_class(
    description: GoodweSensorDescription,
) -> type[GoodweSensor | GoodweTotalSensor | GoodweDailyResetSensor]:
    """Pick the entity class a description's semantics ask for."""
    if description.daily_reset:
        return GoodweDailyResetSensor
    if description.state_class in (
        SensorStateClass.TOTAL,
        SensorStateClass.TOTAL_INCREASING,
    ):
        return GoodweTotalSensor
    return GoodweSensor


class GoodweSensor(GoodweEntity, SensorEntity):
    """Goodwe sensor."""

    entity_description: GoodweSensorDescription

    @property
    @override
    def native_value(self) -> str | int | float | date | None:
        """Return the native value of the sensor."""
        value = self.entity_description.value_fn(self.coordinator.device)
        if isinstance(value, IntEnum):
            return value.name.lower()
        return value


class GoodweTotalSensor(GoodweEntity, RestoreSensor):
    """Goodwe sensor cumulative total sensor."""

    entity_description: GoodweSensorDescription

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is None:
            return
        if last_data.native_value is None:
            return
        try:
            val = float(str(last_data.native_value))
        except ValueError, TypeError:
            return
        self._attr_native_value = val

    @property
    @override
    def native_value(self) -> int | float | None:
        value = self.entity_description.value_fn(self.coordinator.device)
        if isinstance(value, (int, float)):
            self._attr_native_value = value
        return cast("int | float | None", self._attr_native_value)

    @property
    @override
    def available(self) -> bool:
        """Stay available when the inverter is offline so the restored value is visible."""
        if self.entity_description.stale_available:
            return True
        return super().available


@dataclass(frozen=True, kw_only=True)
class GoodweSensorDescription(SensorEntityDescription, GoodweEntityDescription):
    """Describe a Goodwe sensor."""

    value_fn: Callable[[GoodweInverter], float | None]
    daily_reset: bool = False
    stale_available: bool = False


class GoodweDailyResetSensor(GoodweTotalSensor):
    """
    Goodwe sensor whose value resets to 0 at midnight.

    The underlying inverter register is a daily cumulative total that the
    inverter itself resets to 0 at midnight.  HA should reset the stored
    value at the same time so the energy dashboard does not see a spike.

    On HA restart after midnight the inverter may not yet answer (e.g. at
    night).  The last known value is restored from the database so the
    energy dashboard has continuity until the inverter comes back online.
    Once the inverter answers the live value always takes over, even when
    it is lower than the restored value (the new day has started).
    """

    _unsub_midnight: Callable[[], None] | None = None

    @override
    async def async_added_to_hass(self) -> None:
        """Restore last value and schedule the midnight reset."""
        await super().async_added_to_hass()
        self._schedule_midnight_reset()

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Cancel the midnight reset when the entity is removed."""
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None
        await super().async_will_remove_from_hass()

    @callback
    def _schedule_midnight_reset(self) -> None:
        """Schedule the value to be reset at the next midnight."""
        if self._unsub_midnight is not None:
            self._unsub_midnight()

        now = dt_util.now()
        next_midnight = dt_util.start_of_local_day(now + timedelta(days=1))
        self._unsub_midnight = async_track_point_in_time(
            self.hass, self._async_reset, next_midnight
        )

    @callback
    def _async_reset(self, now: date) -> None:
        """Reset the sensor value to 0 and re-schedule for the next midnight."""
        self._attr_native_value = 0.0
        self.async_write_ha_state()
        self._schedule_midnight_reset()


SENSOR_DESCRIPTIONS: tuple[GoodweSensorDescription, ...] = (
    GoodweSensorDescription(
        key="voltage_l1",
        component="grid",
        translation_key="voltage_l",
        translation_placeholders={"phase": "1"},
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.voltage_l1,
    ),
    GoodweSensorDescription(
        key="voltage_l2",
        component="grid",
        translation_key="voltage_l",
        translation_placeholders={"phase": "2"},
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.voltage_l2,
    ),
    GoodweSensorDescription(
        key="voltage_l3",
        component="grid",
        translation_key="voltage_l",
        translation_placeholders={"phase": "3"},
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.voltage_l3,
    ),
    GoodweSensorDescription(
        key="current_l1",
        component="grid",
        translation_key="current_l",
        translation_placeholders={"phase": "1"},
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.current_l1,
    ),
    GoodweSensorDescription(
        key="current_l2",
        component="grid",
        translation_key="current_l",
        translation_placeholders={"phase": "2"},
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.current_l2,
    ),
    GoodweSensorDescription(
        key="current_l3",
        component="grid",
        translation_key="current_l",
        translation_placeholders={"phase": "3"},
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.current_l3,
    ),
    GoodweSensorDescription(
        key="frequency_l1",
        component="grid",
        translation_key="frequency_l",
        translation_placeholders={"phase": "1"},
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.frequency_l1,
    ),
    GoodweSensorDescription(
        key="frequency_l2",
        component="grid",
        translation_key="frequency_l",
        translation_placeholders={"phase": "2"},
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.frequency_l2,
    ),
    GoodweSensorDescription(
        key="frequency_l3",
        component="grid",
        translation_key="frequency_l",
        translation_placeholders={"phase": "3"},
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.frequency_l3,
    ),
    GoodweSensorDescription(
        key="power_l1",
        component="grid",
        translation_key="power_l",
        translation_placeholders={"phase": "1"},
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.power_l1,
    ),
    GoodweSensorDescription(
        key="power_l2",
        component="grid",
        translation_key="power_l",
        translation_placeholders={"phase": "2"},
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.power_l2,
    ),
    GoodweSensorDescription(
        key="power_l3",
        component="grid",
        translation_key="power_l",
        translation_placeholders={"phase": "3"},
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.power_l3,
    ),
    GoodweSensorDescription(
        key="power",
        component="grid_fast",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.grid.power,
    ),
    GoodweSensorDescription(
        key="system_state",
        component="state",
        translation_key="system_state",
        device_class=SensorDeviceClass.ENUM,
        options=[state.name.lower() for state in SystemState],
        value_fn=lambda device: device.state.system_state,
    ),
    GoodweSensorDescription(
        key="generation_time_total",
        component="state",
        translation_key="generation_time_total",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.state.generation_time_total,
    ),
    GoodweSensorDescription(
        key="inverter_temperature",
        component="state",
        translation_key="inverter_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.state.inverter_temperature,
    ),
    GoodweSensorDescription(
        key="pv_voltage_1",
        component="pv",
        translation_key="pv_voltage",
        translation_placeholders={"string": "1"},
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[0].pv_voltage,
    ),
    GoodweSensorDescription(
        key="pv_current_1",
        component="pv",
        translation_key="pv_current",
        translation_placeholders={"string": "1"},
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[0].pv_current,
    ),
    GoodweSensorDescription(
        key="pv_power_1",
        component="pv",
        translation_key="pv_power",
        translation_placeholders={"string": "1"},
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[0].pv_power,
    ),
    GoodweSensorDescription(
        key="pv_voltage_2",
        component="pv",
        translation_key="pv_voltage",
        translation_placeholders={"string": "2"},
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[1].pv_voltage,
    ),
    GoodweSensorDescription(
        key="pv_current_2",
        component="pv",
        translation_key="pv_current",
        translation_placeholders={"string": "2"},
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[1].pv_current,
    ),
    GoodweSensorDescription(
        key="pv_power_2",
        component="pv",
        translation_key="pv_power",
        translation_placeholders={"string": "2"},
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.pv.strings[1].pv_power,
    ),
    GoodweSensorDescription(
        key="energy_today",
        component="energy",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        daily_reset=True,
        stale_available=True,
        value_fn=lambda device: device.energy.daily_energy,
    ),
    GoodweSensorDescription(
        key="energy_total",
        component="energy",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        stale_available=True,
        value_fn=lambda device: device.energy.lifetime_energy,
    ),
)
