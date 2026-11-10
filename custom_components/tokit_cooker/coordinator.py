"""Polls the cooker over the LAN."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COOKING_INTERVAL, DOMAIN, IDLE_INTERVAL, PROPERTIES, STATUS_HEATING
from .miio import MiioDevice, MiioError

_LOGGER = logging.getLogger(__name__)

type TokitConfigEntry = ConfigEntry[TokitCoordinator]


class TokitCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: TokitConfigEntry

    def __init__(self, hass: HomeAssistant, entry: TokitConfigEntry, device: MiioDevice, info: dict[str, Any]) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=IDLE_INTERVAL)
        self.device = device
        self.info = info

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
        # Poll faster while it's heating, so temperature and power stay current.
        self.update_interval = COOKING_INTERVAL if data["status"] in STATUS_HEATING else IDLE_INTERVAL
        return data

    async def async_action(self, action: tuple[int, int], inputs: list[tuple[int, Any]] | None = None) -> None:
        try:
            await self.hass.async_add_executor_job(self.device.action, action[0], action[1], inputs or [])
        except MiioError as err:
            raise HomeAssistantError(f"The cooker didn't accept that: {err}") from err
        await self.async_request_refresh()
