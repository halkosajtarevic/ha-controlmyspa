"""The ControlMySpa integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ControlMySpaApi, ControlMySpaAuthError, ControlMySpaError
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SPA_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ControlMySpaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORM_LIST: list[Platform] = [Platform(platform) for platform in PLATFORMS]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ControlMySpa from a config entry."""
    session = async_get_clientsession(hass)
    api = ControlMySpaApi(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    try:
        await api.async_login()
    except ControlMySpaAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False
    except ControlMySpaError as err:
        raise ConfigEntryNotReady(f"Cannot reach ControlMySpa: {err}") from err

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())
    coordinator = ControlMySpaCoordinator(
        hass, api, entry.data[CONF_SPA_ID], timedelta(seconds=int(scan_interval))
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORM_LIST)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORM_LIST):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
