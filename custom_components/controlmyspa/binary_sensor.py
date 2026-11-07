"""Binary sensors for ControlMySpa."""
from __future__ import annotations

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

SIMPLE = (
    ("online", BinarySensorDeviceClass.CONNECTIVITY, lambda d: bool(d.get("isOnline"))),
    ("panel_locked", BinarySensorDeviceClass.LOCK, lambda d: bool(d.get("isPanelLocked"))),
    ("priming", BinarySensorDeviceClass.RUNNING, lambda d: bool(d.get("isPrimingMode"))),
    (
        "fault",
        BinarySensorDeviceClass.PROBLEM,
        lambda d: bool(d.get("currentFaultMessage")),
    ),
)

READ_ONLY_COMPONENTS = (
    ("OZONE", "ozone", BinarySensorDeviceClass.POWER),
    ("CIRCULATION_PUMP", "circulation_pump", BinarySensorDeviceClass.RUNNING),
    ("FILTER", "filter", BinarySensorDeviceClass.RUNNING),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for spa_id in coordinator.spa_ids:
        for key, device_class, value_fn in SIMPLE:
            entities.append(
                ControlMySpaSimpleBinary(coordinator, spa_id, key, device_class, value_fn)
            )
        dashboard = (coordinator.data or {}).get(spa_id) or {}
        for component_type, label, device_class in READ_ONLY_COMPONENTS:
            count = sum(
                1
                for c in dashboard.get("components", [])
                if c.get("componentType") == component_type
            )
            for index in range(count):
                entities.append(
                    ControlMySpaComponentBinary(
                        coordinator, spa_id, component_type, index, label, device_class
                    )
                )

    async_add_entities(entities)


class ControlMySpaSimpleBinary(ControlMySpaEntity, BinarySensorEntity):
    """A boolean derived from the dashboard payload."""

    def __init__(self, coordinator, spa_id, key, device_class, value_fn) -> None:
        super().__init__(coordinator, spa_id, f"binary_{key}")
        self._attr_translation_key = key
        self._attr_device_class = device_class
        self._value_fn = value_fn

    @property
    def is_on(self) -> bool:
        return bool(self._value_fn(self.dashboard))


class ControlMySpaComponentBinary(ControlMySpaEntity, BinarySensorEntity):
    """State of a component that cannot be commanded (ozone, filters, circ pump)."""

    def __init__(self, coordinator, spa_id, component_type, index, label, device_class) -> None:
        super().__init__(coordinator, spa_id, f"{component_type.lower()}_{index}")
        self._component_type = component_type
        self._index = index
        self._attr_name = f"{label.replace('_', ' ').title()} {index + 1}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        comp = self.component(self._component_type, self._index) or {}
        return str(comp.get("value")).upper() in ("ON", "HIGH", "DISABLED")
