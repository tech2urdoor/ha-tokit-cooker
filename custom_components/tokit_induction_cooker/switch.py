"""Mute: the cooker's beeper setting. It changes nothing about the heat."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PROP_MUTED
from .coordinator import TokitConfigEntry, TokitCoordinator
from .entity import TokitEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TokitConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([TokitMuteSwitch(entry.runtime_data)])


class TokitMuteSwitch(TokitEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TokitCoordinator) -> None:
        super().__init__(coordinator, "muted")

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get("muted")
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_MUTED, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_MUTED, False)
