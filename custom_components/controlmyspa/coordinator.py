"""Data update coordinator for ControlMySpa (one or more spas)."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ControlMySpaApi, ControlMySpaAuthError, ControlMySpaError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ControlMySpaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll every configured spa and keep their dashboards."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ControlMySpaApi,
        spa_ids: list[str],
        spa_meta: dict[str, dict[str, Any]] | None = None,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({len(spa_ids)} spa{'s' if len(spa_ids) != 1 else ''})",
            update_interval=scan_interval,
        )
        self.api = api
        self.spa_ids = spa_ids
        self.spa_meta: dict[str, dict[str, Any]] = spa_meta or {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch every spa; fail only when none of them answered."""
        data: dict[str, dict[str, Any]] = {}
        auth_error: Exception | None = None
        last_error: Exception | None = None

        for spa_id in self.spa_ids:
            try:
                dashboard = await self.api.async_get_dashboard(spa_id)
            except ControlMySpaAuthError as err:
                auth_error = err
                break
            except ControlMySpaError as err:
                last_error = err
                _LOGGER.debug("Spa %s did not answer: %s", spa_id, err)
                continue
            if dashboard:
                data[spa_id] = dashboard

        if auth_error is not None:
            raise UpdateFailed(f"authentication failed: {auth_error}") from auth_error

        if not data:
            raise UpdateFailed(f"no spa answered ({last_error})")

        if len(data) < len(self.spa_ids):
            _LOGGER.debug("%s of %s spas answered", len(data), len(self.spa_ids))

        return data

    def spa_name(self, spa_id: str) -> str:
        """Best human-readable name for a spa (alias, else serial)."""
        meta = self.spa_meta.get(spa_id) or {}
        return (
            meta.get("alias")
            or meta.get("name")
            or meta.get("serialNumber")
            or spa_id
        )
