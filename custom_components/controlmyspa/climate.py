"""Climate platform for ControlMySpa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import ControlMySpaCoordinator
from .entity import ControlMySpaEntity
from .util import from_celsius, is_celsius, to_celsius

_LOGGER = logging.getLogger(__name__)

PRESET_READY = "ready"
PRESET_REST = "rest"

# Panel ranges, in Fahrenheit, straight from the dashboard's rangeLimits block.
LOW_RANGE = (50.0, 99.0)
HIGH_RANGE = (80.0, 104.0)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the climate entity."""
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ControlMySpaClimate(coordinator)])


class ControlMySpaClimate(ControlMySpaEntity, ClimateEntity):
    """Thermostat for the spa water."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_preset_modes = [PRESET_READY, PRESET_REST]
    _attr_translation_key = "spa_climate"

    def __init__(self, coordinator: ControlMySpaCoordinator) -> None:
        super().__init__(coordinator, "climate")

    @property
    def _celsius(self) -> bool:
        return is_celsius(self.dashboard)

    @property
    def current_temperature(self) -> float | None:
        return to_celsius(self.dashboard.get("currentTemp"), self._celsius)

    @property
    def target_temperature(self) -> float | None:
        return to_celsius(self.dashboard.get("desiredTemp"), self._celsius)

    @property
    def min_temp(self) -> float:
        low, _ = LOW_RANGE if (self.dashboard.get("tempRange") or "LOW") == "LOW" else HIGH_RANGE
        return to_celsius(low, False) or 10.0

    @property
    def max_temp(self) -> float:
        _, high = LOW_RANGE if (self.dashboard.get("tempRange") or "LOW") == "LOW" else HIGH_RANGE
        return to_celsius(high, False) or 40.0

    @property
    def target_temperature_step(self) -> float:
        return 0.5

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        mode = self.dashboard.get("heaterMode")
        if mode == "READY":
            return PRESET_READY
        if mode == "REST":
            return PRESET_REST
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "temperature_range": self.dashboard.get("tempRange"),
            "panel_locked": self.dashboard.get("isPanelLocked"),
            "priming_mode": self.dashboard.get("isPrimingMode"),
            "fault": self.dashboard.get("currentFaultMessage"),
            "alerts": self.dashboard.get("totalAlerts"),
            "spa_online": self.dashboard.get("isOnline"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        api_value = from_celsius(float(temperature), self._celsius)
        try:
            await self.coordinator.api.async_set_temperature(self._spa_id, api_value)
        except Exception as err:  # noqa: BLE001 - surfaced to the user
            raise HomeAssistantError(f"Failed to set temperature: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Switch between READY (maintain heat) and REST (heat on demand)."""
        try:
            await self.coordinator.api.async_set_heater_mode(
                self._spa_id, preset_mode == PRESET_READY
            )
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Failed to set heater mode: {err}") from err
        await self.coordinator.async_request_refresh()
