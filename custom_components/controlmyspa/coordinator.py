"""Data update coordinator for ControlMySpa."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ControlMySpaApi, ControlMySpaAuthError, ControlMySpaError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ControlMySpaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the spa dashboard on a fixed interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ControlMySpaApi,
        spa_id: str,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {spa_id}",
            update_interval=scan_interval,
        )
        self.api = api
        self.spa_id = spa_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            dashboard = await self.api.async_get_dashboard(self.spa_id)
        except ControlMySpaAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except ControlMySpaError as err:
            raise UpdateFailed(f"cannot reach ControlMySpa: {err}") from err

        if not dashboard:
            raise UpdateFailed("empty dashboard response")
        return dashboard
