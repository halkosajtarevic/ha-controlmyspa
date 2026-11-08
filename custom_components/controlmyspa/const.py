"""Constants for the ControlMySpa integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "controlmyspa"

API_BASE = "https://iot.controlmyspa.com"
REQUEST_TIMEOUT = 30

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SPA_IDS = "spa_ids"
CONF_SCAN_INTERVAL = "scan_interval"

# legacy single-spa key, kept so older entries keep working
CONF_SPA_ID = "spa_id"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MIN_SCAN_INTERVAL = 30

MANUFACTURER = "Balboa Water Group"
MODEL = "ControlMySpa Gateway"

# The cloud always accepts and returns Fahrenheit. Spas set to Celsius report
# isCelsius=true, but some gateways send Fahrenheit numbers while still setting the
# flag. A spa never exceeds ~45 C, so anything above that is treated as Fahrenheit.
CELSIUS_SANITY_LIMIT = 45.0

PLATFORMS = ["binary_sensor", "climate", "sensor", "switch"]

# After a command the cloud answers at once ("SENT") but the spa itself reports
# the new state a few seconds later. Poll briskly for a short while instead of
# waiting for the next scheduled refresh.
COMMAND_POLL_INTERVAL = 2.0
COMMAND_POLL_TIMEOUT = 30.0
