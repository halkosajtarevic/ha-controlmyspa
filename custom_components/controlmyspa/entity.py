"""Base entity for ControlMySpa."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ControlMySpaCoordinator


class ControlMySpaEntity(CoordinatorEntity[ControlMySpaCoordinator]):
    """Common behaviour for all ControlMySpa entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ControlMySpaCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._spa_id = coordinator.spa_id
        self._attr_unique_id = f"{self._spa_id}_{unique_suffix}"

    @property
    def dashboard(self) -> dict[str, Any]:
        """Shortcut to the coordinator payload."""
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        """Entities stay available while the cloud reports data."""
        return super().available and bool(self.dashboard)

    @property
    def device_info(self) -> DeviceInfo:
        """Group every entity under one device."""
        data = self.dashboard
        system_info = data.get("systemInfo") or {}
        cms_code = data.get("cmsCode")
        serial = data.get("serialNumber") or self._spa_id
        return DeviceInfo(
            identifiers={(DOMAIN, self._spa_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=cms_code or serial,
            serial_number=serial,
            sw_version=system_info.get("controllerSoftwareVersion"),
        )

    def component(self, component_type: str, index: int = 0) -> dict[str, Any] | None:
        """Return the n-th component of a given dashboard type."""
        matches = [
            comp
            for comp in self.dashboard.get("components", [])
            if comp.get("componentType") == component_type
        ]
        if index < len(matches):
            return matches[index]
        return None

    def component_count(self, component_type: str) -> int:
        """How many components of a type the spa reports."""
        return sum(
            1
            for comp in self.dashboard.get("components", [])
            if comp.get("componentType") == component_type
        )
