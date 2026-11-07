"""Base entity for ControlMySpa."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ControlMySpaCoordinator


class ControlMySpaEntity(CoordinatorEntity[ControlMySpaCoordinator]):
    """Common behaviour for entities belonging to one spa."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ControlMySpaCoordinator, spa_id: str, unique_suffix: str
    ) -> None:
        super().__init__(coordinator)
        self._spa_id = spa_id
        self._attr_unique_id = f"{spa_id}_{unique_suffix}"

    @property
    def spa_meta(self) -> dict[str, Any]:
        """Account-side metadata for this spa."""
        return self.coordinator.spa_meta.get(self._spa_id) or {}

    @property
    def dashboard(self) -> dict[str, Any]:
        """Latest dashboard payload for this spa."""
        return (self.coordinator.data or {}).get(self._spa_id) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.dashboard)

    @property
    def device_info(self) -> DeviceInfo:
        """Group the entities of one spa into one device."""
        data = self.dashboard
        system_info = data.get("systemInfo") or {}
        serial = data.get("serialNumber") or self.spa_meta.get("serialNumber") or self._spa_id
        return DeviceInfo(
            identifiers={(DOMAIN, self._spa_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=self.coordinator.spa_name(self._spa_id),
            serial_number=serial,
            sw_version=system_info.get("controllerSoftwareVersion"),
        )

    def component(self, component_type: str, index: int = 0) -> dict[str, Any] | None:
        """Return the n-th component of a dashboard type."""
        matches = [
            comp
            for comp in self.dashboard.get("components", [])
            if comp.get("componentType") == component_type
        ]
        return matches[index] if index < len(matches) else None

    def component_count(self, component_type: str) -> int:
        return sum(
            1
            for comp in self.dashboard.get("components", [])
            if comp.get("componentType") == component_type
        )
