"""Polls the cooker over the LAN."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ACTIVE_INTERVAL, DOMAIN, FOLLOW_UP_SECONDS, IDLE_INTERVAL, PROPERTIES, STATUS_ADJUSTABLE
from .miio import MiioDevice, MiioError

_LOGGER = logging.getLogger(__name__)

type TokitConfigEntry = ConfigEntry[TokitCoordinator]


class TokitCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: TokitConfigEntry

    def __init__(self, hass: HomeAssistant, entry: TokitConfigEntry, device: MiioDevice, info: dict[str, Any]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=IDLE_INTERVAL)
        self.device = device
        self.info = info
        self._cancel_follow_up: CALLBACK_TYPE | None = None

    def _read(self) -> dict[str, Any]:
        values = self.device.get_properties(list(PROPERTIES.values()))
        return {key: values.get(pair) for key, pair in PROPERTIES.items()}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.hass.async_add_executor_job(self._read)
        except MiioError as err:
            raise UpdateFailed(str(err)) from err
        if data.get("status") is None:
            raise UpdateFailed("the cooker returned no status")
        # Read faster while it's cooking or paused, so temperature, power and the timer stay current.
        self.update_interval = ACTIVE_INTERVAL if data["status"] in STATUS_ADJUSTABLE else IDLE_INTERVAL
        return data

    async def async_action(self, action: tuple[int, int], inputs: list[tuple[int, Any]] | None = None) -> None:
        try:
            await self.hass.async_add_executor_job(self.device.action, action[0], action[1], inputs or [])
        except MiioError as err:
            raise HomeAssistantError(f"The cooker didn't accept that: {err}") from err
        await self._read_now_and_again_soon()

    async def async_set_property(self, prop: tuple[int, int], value: Any) -> None:
        try:
            await self.hass.async_add_executor_job(self.device.set_property, prop[0], prop[1], value)
        except MiioError as err:
            raise HomeAssistantError(f"The cooker didn't accept that: {err}") from err
        await self._read_now_and_again_soon()

    async def _read_now_and_again_soon(self) -> None:
        # Not async_request_refresh: its debouncer skips the read for a second command within
        # ten seconds of the first, so pause then resume would show "paused" until the follow-up.
        await self.async_refresh()
        if self._cancel_follow_up:
            self._cancel_follow_up()
        self._cancel_follow_up = async_call_later(self.hass, FOLLOW_UP_SECONDS, self._follow_up)

    async def _follow_up(self, _now: datetime) -> None:
        self._cancel_follow_up = None
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        if self._cancel_follow_up:
            self._cancel_follow_up()
            self._cancel_follow_up = None
        await super().async_shutdown()
