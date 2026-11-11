"""Power level and target temperature. They only work while the cooker is already cooking or paused."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ACTION_SET_POWER,
    ACTION_SET_TEMPERATURE,
    PIID_INFORMATION,
    PIID_POWER_LEVEL,
    PIID_TARGET_TEMPERATURE,
    PIID_USER_ID,
    STATUS_ADJUSTABLE,
)
from .coordinator import TokitConfigEntry, TokitCoordinator
from .entity import TokitEntity


@dataclass(frozen=True, kw_only=True)
class TokitNumberDescription(NumberEntityDescription):
    action: tuple[int, int]
    piid: int


NUMBERS: tuple[TokitNumberDescription, ...] = (
    TokitNumberDescription(
        key="power_level",
        native_min_value=1,
        native_max_value=99,
        native_step=1,
        mode=NumberMode.SLIDER,
        action=ACTION_SET_POWER,
        piid=PIID_POWER_LEVEL,
    ),
    TokitNumberDescription(
        key="target_temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        # A guess at safe bounds: a real cooker accepted 80, and its built-in modes use 155 to 199.
        native_min_value=40,
        native_max_value=200,
        native_step=1,
        mode=NumberMode.BOX,
        action=ACTION_SET_TEMPERATURE,
        piid=PIID_TARGET_TEMPERATURE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: TokitConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(TokitNumber(entry.runtime_data, description) for description in NUMBERS)


class TokitNumber(TokitEntity, NumberEntity):
    entity_description: TokitNumberDescription

    def __init__(self, coordinator: TokitCoordinator, description: TokitNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        # A number must never be the thing that switches the heat on.
        if self.coordinator.data.get("status") not in STATUS_ADJUSTABLE:
            raise HomeAssistantError("The cooker isn't cooking, so there's nothing to adjust")
        description = self.entity_description
        await self.coordinator.async_action(
            description.action,
            [(description.piid, int(value)), (PIID_INFORMATION, ""), (PIID_USER_ID, "")],
        )
