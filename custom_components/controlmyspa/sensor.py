"""Sensor platform for ControlMySpa."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ControlMySpaCoordinator
from .entity import ControlMySpaEntity


def _fault(d: dict[str, Any]) -> str:
    return d.get("currentFaultMessage") or "none"


def _last_ping(d: dict[str, Any]) -> datetime | None:
    raw = (d.get("systemInfo") or {}).get("pingTime")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="fault_message",
        translation_key="fault_message",
        icon="mdi:alert-circle-outline",
        value_fn=_fault,
    ),
    SensorEntityDescription(
        key="alerts",
        translation_key="alerts",
        icon="mdi:bell-ring-outline",
        native_unit_of_measurement="alerts",
        value_fn=lambda d: d.get("totalAlerts"),
    ),
    SensorEntityDescription(
        key="temp_range",
        translation_key="temp_range",
        icon="mdi:thermometer-chevron-up",
        device_class=SensorDeviceClass.ENUM,
        options=["LOW", "HIGH"],
        value_fn=lambda d: d.get("tempRange"),
    ),
    SensorEntityDescription(
        key="heater_mode",
        translation_key="heater_mode",
        icon="mdi:fire",
        device_class=SensorDeviceClass.ENUM,
        options=["REST", "READY"],
        value_fn=lambda d: d.get("heaterMode"),
    ),
    SensorEntityDescription(
        key="software_version",
        translation_key="software_version",
        icon="mdi:chip",
        entity_category=None,
        value_fn=lambda d: (d.get("systemInfo") or {}).get("controllerSoftwareVersion"),
    ),
    SensorEntityDescription(
        key="last_ping",
        translation_key="last_ping",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_ping,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ControlMySpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ControlMySpaSensor(coordinator, desc) for desc in SENSORS)


class ControlMySpaSensor(ControlMySpaEntity, SensorEntity):
    """One read-only value from the spa dashboard."""

    entity_description: SensorEntityDescription

    def __init__(
        self, coordinator: ControlMySpaCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator, f"sensor_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        value_fn: Callable[[dict[str, Any]], Any] = self.entity_description.value_fn  # type: ignore[attr-defined]
        return value_fn(self.dashboard)
