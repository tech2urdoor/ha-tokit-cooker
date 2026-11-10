"""Binary sensors: heating, and whether the cooker reports a fault."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATUS_HEATING
from .coordinator import TokitConfigEntry
from .entity import TokitEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TokitConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([TokitHeating(entry.runtime_data, "heating"), TokitProblem(entry.runtime_data, "problem")])


class TokitHeating(TokitEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("status") in STATUS_HEATING


class TokitProblem(TokitEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("fault"))
