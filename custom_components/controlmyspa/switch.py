"""Switch platform for ControlMySpa components."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ControlMySpaCoordinator
from .entity import ControlMySpaEntity

_LOGGER = logging.getLogger(__name__)

# dashboard component type -> (command componentType, label, on state)
SETTABLE = {
    "PUMP": ("jet", "Pump", "HIGH"),
    "LIGHT": ("light", "Light", "HIGH"),
    "BLOWER": ("blower", "Blower", "HIGH"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    components = coordinator.data.get("components") or []
    for component_type, (command_name, label, _on) in SETTABLE.items():
        count = sum(1 for c in components if c.get("componentType") == component_type)
        for index in range(count):
            entities.append(
                ControlMySpaSwitch(coordinator, component_type, command_name, label, index)
            )
    async_add_entities(entities)


class ControlMySpaSwitch(ControlMySpaEntity, SwitchEntity):
    """A pump, light or blower that can be switched on and off."""

    def __init__(
        self,
        coordinator: ControlMySpaCoordinator,
        component_type: str,
        command_name: str,
        label: str,
        index: int,
    ) -> None:
        super().__init__(coordinator, f"{component_type.lower()}_{index}")
        self._component_type = component_type
        self._command_name = command_name
        self._index = index
        self._attr_name = f"{label} {index + 1}"
        self._attr_icon = {
            "PUMP": "mdi:pump",
            "LIGHT": "mdi:lightbulb",
            "BLOWER": "mdi:fan",
        }.get(component_type, "mdi:toggle-switch")

    @property
    def _component(self) -> dict[str, Any]:
        return self.component(self._component_type, self._index) or {}

    @property
    def is_on(self) -> bool:
        return str(self._component.get("value")).upper() in ("HIGH", "ON")

    @property
    def available(self) -> bool:
        return super().available and bool(self._component.get("availableValues"))

    async def _async_set(self, state: str) -> None:
        try:
            await self.coordinator.api.async_set_component_state(
                self._spa_id, self._command_name, self._index, state
            )
        except Exception as err:  # noqa: BLE001 - surfaced to the user
            raise HomeAssistantError(f"Failed to switch {self.name}: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set("HIGH")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set("OFF")
