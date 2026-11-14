"""TOKIT induction cooker (chunmi.ihcooker.cbhw), controlled over the LAN with no cloud."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import ACTION_START_COOK, CONF_INFO, COOK_MODES, DOMAIN, INFO_REMEMBERED, PIID_COOK_MODE
from .coordinator import TokitConfigEntry, TokitCoordinator
from .miio import MiioDevice, MiioError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SELECT_MODE = "select_mode"
SELECT_MODE_SCHEMA = vol.Schema({vol.Required("mode"): vol.In(COOK_MODES), vol.Optional("device_id"): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def select_mode(call: ServiceCall) -> None:
        """Wake the cooker and select one of its built-in modes.

        This doesn't heat anything. The cooker beeps and waits for a press on its own
        start button, so nothing in Home Assistant can start the hob by itself. It is
        still a service and not a switch, so "turn everything in the kitchen on" can't
        even wake it.
        """
        entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
        if device_id := call.data.get("device_id"):
            device = dr.async_get(hass).async_get(device_id)
            entries = [e for e in entries if device is not None and e.entry_id in device.config_entries]
        if not entries:
            raise HomeAssistantError("The cooker isn't set up or isn't reachable")
        if len(entries) > 1:
            raise ServiceValidationError("There is more than one cooker, so say which one with device_id")
        coordinator: TokitCoordinator = entries[0].runtime_data
        await coordinator.async_action(ACTION_START_COOK, [(PIID_COOK_MODE, COOK_MODES[call.data["mode"]])])

    hass.services.async_register(DOMAIN, SERVICE_SELECT_MODE, select_mode, schema=SELECT_MODE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TokitConfigEntry) -> bool:
    device = MiioDevice(entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    try:
        info = await hass.async_add_executor_job(device.info)
    except MiioError as err:
        # Switched off at the wall, most likely. Set up from what the last setup remembered, with the entities
        # unavailable until it answers, rather than leave the entry failing and retrying for as long as it's off.
        if not (info := entry.data.get(CONF_INFO) or _info_from_device_registry(hass, entry)):
            raise ConfigEntryNotReady(f"Cooker at {entry.data[CONF_HOST]} isn't answering: {err}") from err
        info = dict(info)
        _LOGGER.info("Cooker at %s isn't answering (%s), so it shows as unavailable until it does", entry.data[CONF_HOST], err)
    else:
        remembered = {key: info[key] for key in INFO_REMEMBERED if key in info}
        if entry.data.get(CONF_INFO) != remembered:
            hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_INFO: remembered})
    coordinator = TokitCoordinator(hass, entry, device, info)
    # Not async_config_entry_first_refresh: a cooker that is off gives a loaded entry with unavailable entities.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True



def _info_from_device_registry(hass: HomeAssistant, entry: TokitConfigEntry) -> dict[str, str] | None:
    """What an entry set up before releases that remember miIO.info can still show, from its device."""
    if not entry.unique_id:
        return None
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.unique_id)})
    if device is None:
        return None
    info = {"mac": entry.unique_id, "model": device.model_id, "fw_ver": device.sw_version, "hw_ver": device.hw_version}
    return {key: value for key, value in info.items() if value}


async def async_unload_entry(hass: HomeAssistant, entry: TokitConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
