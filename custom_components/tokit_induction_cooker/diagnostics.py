"""What to attach to a bug report. The token, addresses and Wi-Fi details are left out."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import TokitConfigEntry

# Only these are copied from what the cooker says about itself. The rest of that answer
# holds the token, the Wi-Fi network and the cooker's addresses.
INFO_KEYS = ("model", "fw_ver", "hw_ver", "wifi_fw_ver", "miio_ver", "life")


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: TokitConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "info": {key: coordinator.info[key] for key in INFO_KEYS if key in coordinator.info},
        "properties": coordinator.data,
        "last_read_worked": coordinator.last_update_success,
        "read_every_seconds": coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
    }
