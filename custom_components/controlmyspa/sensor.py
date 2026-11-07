"""Sensor platform for ControlMySpa."""
from __future__ import annotations

from dataclasses import dataclass
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
from .util import fault_description, fault_details
from .coordinator import ControlMySpaCoordinator
from .entity import ControlMySpaEntity


@dataclass(frozen=True, kw_only=True)
class ControlMySpaSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor for the spa dashboard."""

    value_fn: Callable[[dict[str, Any]], Any]


def _fault(d: dict[str, Any]) -> str:
    return fault_description(d)


def _last_ping(d: dict[str, Any]) -> datetime | None:
    raw = (d.get("systemInfo") or {}).get("pingTime")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


SENSORS: tuple[ControlMySpaSensorDescription, ...] = (
    ControlMySpaSensorDescription(
        key="fault_message",
        translation_key="fault_message",
        icon="mdi:alert-circle-outline",
        value_fn=_fault,
    ),
    ControlMySpaSensorDescription(
        key="alerts",
        translation_key="alerts",
        icon="mdi:bell-ring-outline",
        value_fn=lambda d: d.get("totalAlerts"),
    ),
    ControlMySpaSensorDescription(
        key="temp_range",
        translation_key="temp_range",
        icon="mdi:thermometer-chevron-up",
        device_class=SensorDeviceClass.ENUM,
        options=["LOW", "HIGH"],
        value_fn=lambda d: d.get("tempRange"),
    ),
    ControlMySpaSensorDescription(
        key="heater_mode",
        translation_key="heater_mode",
        icon="mdi:fire",
        device_class=SensorDeviceClass.ENUM,
        options=["REST", "READY", "READY_REST"],
        value_fn=lambda d: d.get("heaterMode"),
    ),
    ControlMySpaSensorDescription(
        key="software_version",
        translation_key="software_version",
        icon="mdi:chip",
        value_fn=lambda d: (d.get("systemInfo") or {}).get("controllerSoftwareVersion"),
    ),
    ControlMySpaSensorDescription(
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
    async_add_entities(
        ControlMySpaSensor(coordinator, spa_id, description)
        for spa_id in coordinator.spa_ids
        for description in SENSORS
    )


class ControlMySpaSensor(ControlMySpaEntity, SensorEntity):
    """One read-only value from a spa dashboard."""

    entity_description: ControlMySpaSensorDescription

    def __init__(
        self,
        coordinator: ControlMySpaCoordinator,
        spa_id: str,
        description: ControlMySpaSensorDescription,
    ) -> None:
        super().__init__(coordinator, spa_id, f"sensor_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.dashboard)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.entity_description.key != "fault_message":
            return {}
        return fault_details(self.dashboard)
