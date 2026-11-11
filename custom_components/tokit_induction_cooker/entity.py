"""Shared entity base."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TokitCoordinator


class TokitEntity(CoordinatorEntity[TokitCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TokitCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = format_mac(coordinator.info["mac"])
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            manufacturer="TOKIT (Chunmi)",
            model="Induction Cooker Pro",
            model_id=coordinator.info.get("model"),
            name="Induction Cooker",
            sw_version=coordinator.info.get("fw_ver"),
        )
