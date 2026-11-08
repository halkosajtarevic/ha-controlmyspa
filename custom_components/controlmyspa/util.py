"""Helpers for ControlMySpa."""
from __future__ import annotations

from typing import Any

from .const import CELSIUS_SANITY_LIMIT


def as_number(value: Any) -> float | None:
    """Parse a temperature the API may send as string, number, None or 0.

    ``0.00`` means "no reading yet" (the spa reports it while idle), not 0 degrees.
    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def is_celsius(dashboard: dict[str, Any]) -> bool:
    """Return True when the reported values are really Celsius.

    The cloud sets ``isCelsius`` from the panel setting, but several gateways
    report Fahrenheit numbers while the flag still says Celsius — and the idle
    value 0.00 makes a naive check believe the numbers are small. Ignore zeros
    and judge by the largest real reading.
    """
    if not dashboard.get("isCelsius"):
        return False

    readings = [
        number
        for number in (
            as_number(dashboard.get("currentTemp")),
            as_number(dashboard.get("desiredTemp")),
            as_number(dashboard.get("setTemp")),
        )
        if number is not None
    ]
    if not readings:
        return True
    return max(readings) <= CELSIUS_SANITY_LIMIT


def to_celsius(value: Any, celsius: bool) -> float | None:
    """Convert an API temperature to Celsius (None when there is no reading)."""
    number = as_number(value)
    if number is None:
        return None
    return round(number, 1) if celsius else round((number - 32) * 5 / 9, 1)


def from_celsius(value: float, celsius: bool) -> float:
    """Convert a Celsius temperature to whatever unit the API speaks.

    The cloud almost always speaks Fahrenheit (even when isCelsius is true), so
    a Celsius value from Home Assistant has to be converted before sending.
    """
    if celsius:
        return round(float(value), 1)
    return round(float(value) * 9 / 5 + 32, 1)


# The cloud sends the fault as either a plain string, null, or a whole
# FaultLogDescription object. Only the description is meant for humans.
FAULT_SEVERITIES = ("WARNING", "ERROR", "CRITICAL", "FAULT")


def fault_description(dashboard: dict[str, Any]) -> str:
    """Human-readable fault text."""
    fault = dashboard.get("currentFaultMessage")
    if not fault:
        return "none"
    if isinstance(fault, dict):
        text = fault.get("description") or fault.get("message") or fault.get("code")
        return str(text) if text else "none"
    return str(fault)


def fault_details(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Structured fault fields for extra state attributes."""
    fault = dashboard.get("currentFaultMessage")
    if not isinstance(fault, dict):
        return {}
    return {
        "code": fault.get("code"),
        "severity": fault.get("severity"),
    }


def has_problem(dashboard: dict[str, Any]) -> bool:
    """True only for a real fault - informational messages are not problems."""
    fault = dashboard.get("currentFaultMessage")
    if not fault:
        return False
    if isinstance(fault, dict):
        severity = str(fault.get("severity") or "").upper()
        if severity in ("INFO", "NONE", "OK"):
            return False
        return severity in FAULT_SEVERITIES or bool(fault.get("code"))
    return True


def component_value(
    data: dict[str, Any], spa_id: str, component_type: str, index: int
) -> str | None:
    """Read one component's value from a coordinator payload.

    Used to confirm a command without waiting for the next scheduled poll.
    """
    dashboard = (data or {}).get(spa_id) or {}
    components = [
        comp
        for comp in dashboard.get("components") or []
        if comp.get("componentType") == component_type
    ]
    if index >= len(components):
        return None
    return str(components[index].get("value") or "").upper()
