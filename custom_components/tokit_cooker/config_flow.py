"""Set the cooker up from its address and miIO token."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN, SUPPORTED_MODELS
from .miio import MiioDevice, MiioError

SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str})


class TokitConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip().lower()
            if not re.fullmatch(r"[0-9a-f]{32}", token):
                errors[CONF_TOKEN] = "invalid_token"
            else:
                try:
                    info = await self.hass.async_add_executor_job(MiioDevice(host, token).info)
                except MiioError:
                    errors["base"] = "cannot_connect"
                else:
                    if info.get("model") not in SUPPORTED_MODELS:
                        return self.async_abort(
                            reason="unsupported_model", description_placeholders={"model": str(info.get("model"))}
                        )
                    await self.async_set_unique_id(format_mac(info["mac"]))
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_TOKEN: token})
                    return self.async_create_entry(
                        title="TOKIT Induction Cooker", data={CONF_HOST: host, CONF_TOKEN: token}
                    )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
