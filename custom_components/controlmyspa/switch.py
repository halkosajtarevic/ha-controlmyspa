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
from .util import component_value

_LOGGER = logging.getLogger(__name__)

# dashboard component type -> (command componentType, translation key, icon)
SETTABLE = {
    "PUMP": ("jet", "pump", "mdi:pump"),
    "LIGHT": ("light", "light", "mdi:lightbulb"),
    "BLOWER": ("blower", "blower", "mdi:fan"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for spa_id in coordinator.spa_ids:
        components = ((coordinator.data or {}).get(spa_id) or {}).get("components") or []
        for component_type, (command_name, label, icon) in SETTABLE.items():
            count = sum(1 for c in components if c.get("componentType") == component_type)
            for index in range(count):
                entities.append(
                    ControlMySpaSwitch(
                        coordinator, spa_id, component_type, command_name, label, icon, index
                    )
                )

    async_add_entities(entities)


class ControlMySpaSwitch(ControlMySpaEntity, SwitchEntity):
    """A pump, light or blower that can be switched on and off."""

    def __init__(self, coordinator, spa_id, component_type, command_name, label, icon, index) -> None:
        super().__init__(coordinator, spa_id, f"{component_type.lower()}_{index}")
        self._component_type = component_type
        self._command_name = command_name
        self._index = index
        self._attr_translation_key = label
        self._attr_translation_placeholders = {"number": str(index + 1)}
        self._attr_icon = icon
        self._assumed: bool | None = None

    @property
    def _component(self) -> dict[str, Any]:
        return self.component(self._component_type, self._index) or {}

    @property
    def is_on(self) -> bool | None:
        """Show the requested state at once, then the spa's own once confirmed."""
        if self._assumed is not None:
            return self._assumed
        return str(self._component.get("value")).upper() in ("HIGH", "ON")

    @property
    def assumed_state(self) -> bool:
        return self._assumed is not None

    @property
    def available(self) -> bool:
        return super().available and bool(self._component.get("availableValues"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)

    async def _async_set(self, turn_on: bool) -> None:
        command_state = "HIGH" if turn_on else "OFF"

        # Optimistic: the UI reflects the intent immediately, not a minute later.
        self._assumed = turn_on
        self.async_write_ha_state()

        try:
            await self.coordinator.api.async_set_component_state(
                self._spa_id, self._command_name, self._index, command_state
            )
        except Exception as err:  # noqa: BLE001 - surfaced to the user
            self._assumed = None
            self.async_write_ha_state()
            raise HomeAssistantError(f"Failed to switch {self.name}: {err}") from err

        # Verify in the background so the service call returns immediately.
        self.hass.async_create_task(self._async_confirm(command_state))

    async def _async_confirm(self, expected: str) -> None:
        """Poll until the spa reports the expected state, then drop the guess."""
        confirmed = await self.coordinator.async_poll_until(
            lambda data: component_value(
                data, self._spa_id, self._component_type, self._index
            )
            == expected
        )
        if not confirmed:
            _LOGGER.warning(
                "Spa did not confirm %s for %s within %ss; showing live state",
                expected,
                self.entity_id,
                self.coordinator.update_interval,
            )
        self._assumed = None
        self.async_write_ha_state()
