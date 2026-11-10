"""TOKIT induction cooker (chunmi.ihcooker.cbhw), controlled over the LAN with no cloud."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import ACTION_START_COOK, COOK_MODES, DOMAIN, PIID_COOK_MODE
from .coordinator import TokitConfigEntry, TokitCoordinator
from .miio import MiioDevice, MiioError

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]
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
        raise ConfigEntryNotReady(f"Cooker at {entry.data[CONF_HOST]} isn't answering: {err}") from err
    coordinator = TokitCoordinator(hass, entry, device, info)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TokitConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
