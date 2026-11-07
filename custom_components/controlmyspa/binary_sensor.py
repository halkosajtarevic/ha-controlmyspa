"""Binary sensors for ControlMySpa."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ControlMySpaCoordinator
from .entity import ControlMySpaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [
        ControlMySpaSimpleBinary(coordinator, "online", BinarySensorDeviceClass.CONNECTIVITY,
                                 lambda d: bool(d.get("isOnline"))),
        ControlMySpaSimpleBinary(coordinator, "panel_locked", BinarySensorDeviceClass.LOCK,
                                 lambda d: bool(d.get("isPanelLocked"))),
        ControlMySpaSimpleBinary(coordinator, "priming", BinarySensorDeviceClass.RUNNING,
                                 lambda d: bool(d.get("isPrimingMode"))),
        ControlMySpaSimpleBinary(coordinator, "fault", BinarySensorDeviceClass.PROBLEM,
                                 lambda d: (d.get("currentFaultMessage") or d.get("totalAlerts")) is not None
                                 and d.get("currentFaultMessage") is not None),
    ]

    # read-only components reported by the spa
    for component_type, label, device_class in (
        ("OZONE", "ozone", BinarySensorDeviceClass.POWER),
        ("CIRCULATION_PUMP", "circulation_pump", BinarySensorDeviceClass.RUNNING),
        ("FILTER", "filter", BinarySensorDeviceClass.RUNNING),
    ):
        count = sum(1 for c in coordinator.data.get("components", []) if c.get("componentType") == component_type)
        for index in range(count):
            entities.append(
                ControlMySpaComponentBinary(coordinator, component_type, index, label, device_class)
            )

    async_add_entities(entities)


class ControlMySpaSimpleBinary(ControlMySpaEntity, BinarySensorEntity):
    """A boolean derived from the dashboard payload."""

    def __init__(self, coordinator: ControlMySpaCoordinator, key: str, device_class, value_fn) -> None:
        super().__init__(coordinator, f"binary_{key}")
        self._attr_translation_key = key
        self._attr_device_class = device_class
        self._value_fn = value_fn

    @property
    def is_on(self) -> bool:
        return bool(self._value_fn(self.dashboard))


class ControlMySpaComponentBinary(ControlMySpaEntity, BinarySensorEntity):
    """State of a component that cannot be commanded (ozone, filters, circ pump)."""

    def __init__(self, coordinator, component_type: str, index: int, label: str, device_class) -> None:
        super().__init__(coordinator, f"{component_type.lower()}_{index}")
        self._component_type = component_type
        self._index = index
        self._attr_name = f"{label.replace('_', ' ').title()} {index + 1}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        comp = self.component(self._component_type, self._index) or {}
        return str(comp.get("value")).upper() in ("ON", "HIGH", "DISABLED")
