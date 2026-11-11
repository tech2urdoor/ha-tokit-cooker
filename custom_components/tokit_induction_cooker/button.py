"""Stop, pause and resume."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ACTION_CANCEL, ACTION_PAUSE, ACTION_RESUME, PIID_INFORMATION, PIID_USER_ID
from .coordinator import TokitConfigEntry, TokitCoordinator
from .entity import TokitEntity


@dataclass(frozen=True, kw_only=True)
class TokitButtonDescription(ButtonEntityDescription):
    action: tuple[int, int]
    inputs: tuple[tuple[int, Any], ...] = ()


BUTTONS: tuple[TokitButtonDescription, ...] = (
    TokitButtonDescription(key="stop", action=ACTION_CANCEL),
    TokitButtonDescription(key="pause", action=ACTION_PAUSE),
    TokitButtonDescription(
        key="resume", action=ACTION_RESUME, inputs=((PIID_INFORMATION, ""), (PIID_USER_ID, ""))
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: TokitConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(TokitButton(entry.runtime_data, description) for description in BUTTONS)


class TokitButton(TokitEntity, ButtonEntity):
    entity_description: TokitButtonDescription

    def __init__(self, coordinator: TokitCoordinator, description: TokitButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_action(self.entity_description.action, list(self.entity_description.inputs))
