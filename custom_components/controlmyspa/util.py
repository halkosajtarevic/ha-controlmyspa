"""Helpers for ControlMySpa."""
from __future__ import annotations

from typing import Any

from .const import CELSIUS_SANITY_LIMIT


def is_celsius(dashboard: dict[str, Any]) -> bool:
    """Return True when the reported values are really Celsius.

    The API sets ``isCelsius`` from the panel setting, but some gateways report
    Fahrenheit numbers while the flag says Celsius. Trust the numbers, not the flag.
    """
    if not dashboard.get("isCelsius"):
        return False
    current = dashboard.get("currentTemp")
    if current is None:
        return True
    return float(current) <= CELSIUS_SANITY_LIMIT


def to_celsius(value: float | None, celsius: bool) -> float | None:
    """Convert an API temperature to Celsius."""
    if value is None:
        return None
    value = float(value)
    return round(value, 1) if celsius else round((value - 32) * 5 / 9, 1)


def from_celsius(value: float, celsius: bool) -> float:
    """Convert a Celsius temperature to the unit the API expects (Fahrenheit)."""
    if celsius:
        return round(float(value) * 9 / 5 + 32, 1)
    return round(float(value), 1)
