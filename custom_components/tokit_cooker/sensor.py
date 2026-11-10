"""Sensors: what the cooker is doing right now."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FAULT, RECIPE_TYPE, STATUS, WORK_STATUS
from .coordinator import TokitConfigEntry, TokitCoordinator
from .entity import TokitEntity


@dataclass(frozen=True, kw_only=True)
class TokitSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]


def _enum(key: str, table: dict[int, str]) -> Callable[[dict[str, Any]], Any]:
    return lambda data: table.get(data.get(key))


SENSORS: tuple[TokitSensorDescription, ...] = (
    TokitSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATUS.values()),
        value=_enum("status", STATUS),
    ),
    TokitSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda data: data.get("temperature"),
    ),
    TokitSensorDescription(
        key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value=lambda data: data.get("target_temperature"),
    ),
    TokitSensorDescription(
        key="power_level",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda data: data.get("power_level"),
    ),
    TokitSensorDescription(
        key="time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value=lambda data: data.get("time_remaining"),
    ),
    TokitSensorDescription(
        key="cooking_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value=lambda data: data.get("cooking_time"),
    ),
    TokitSensorDescription(
        key="fault",
        device_class=SensorDeviceClass.ENUM,
        options=list(FAULT.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_enum("fault", FAULT),
    ),
    TokitSensorDescription(
        key="work_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(WORK_STATUS.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value=_enum("work_status", WORK_STATUS),
    ),
    TokitSensorDescription(
        key="recipe_type",
        device_class=SensorDeviceClass.ENUM,
        options=list(RECIPE_TYPE.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value=_enum("recipe_type", RECIPE_TYPE),
    ),
    TokitSensorDescription(
        key="phase",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value=lambda data: data.get("phase"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: TokitConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(TokitSensor(entry.runtime_data, description) for description in SENSORS)


class TokitSensor(TokitEntity, SensorEntity):
    entity_description: TokitSensorDescription

    def __init__(self, coordinator: TokitCoordinator, description: TokitSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.coordinator.data)
