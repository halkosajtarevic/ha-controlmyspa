"""Constants for the ControlMySpa integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "controlmyspa"

API_BASE = "https://iot.controlmyspa.com"
REQUEST_TIMEOUT = 30

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SPA_ID = "spa_id"
CONF_SPA_LABEL = "spa_label"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MIN_SCAN_INTERVAL = 30

MANUFACTURER = "Balboa Water Group"
MODEL = "ControlMySpa Gateway"

# The cloud API always accepts and returns temperatures in Fahrenheit.
# Spas configured for Celsius report isCelsius=true, but some gateways report
# Fahrenheit values while still setting the flag. A spa can never exceed ~45 C,
# so anything above that threshold is treated as Fahrenheit regardless of the flag.
CELSIUS_SANITY_LIMIT = 45.0

PLATFORMS = ["binary_sensor", "climate", "sensor", "switch"]
