"""Set the cooker up from its address and miIO token."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import DOMAIN, SUPPORTED_MODELS
from .miio import MiioDevice, MiioError

SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str})


class TokitConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    _host: str | None = None

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """The router saw the cooker. A cooker already set up just has its address kept current."""
        await self.async_set_unique_id(format_mac(discovery_info.macaddress))
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})
        self._host = discovery_info.ip
        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A new token or address for a cooker that's already set up."""
        self._host = self._get_reconfigure_entry().data[CONF_HOST]
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = self._host = user_input[CONF_HOST].strip()
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
                    data = {CONF_HOST: host, CONF_TOKEN: token}
                    await self.async_set_unique_id(format_mac(info["mac"]))
                    if self.source == SOURCE_RECONFIGURE:
                        self._abort_if_unique_id_mismatch(reason="wrong_device")
                        return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data=data)
                    self._abort_if_unique_id_configured(updates=data)
                    return self.async_create_entry(title="TOKIT Induction Cooker", data=data)
        schema = self.add_suggested_values_to_schema(SCHEMA, {CONF_HOST: self._host})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
