"""Async client for the ControlMySpa cloud API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class ControlMySpaError(Exception):
    """Base error for ControlMySpa."""


class ControlMySpaAuthError(ControlMySpaError):
    """Authentication failed."""


class ControlMySpaConnectionError(ControlMySpaError):
    """Cannot reach the ControlMySpa cloud."""


class ControlMySpaCommandError(ControlMySpaError):
    """A command was rejected by the cloud."""


class ControlMySpaApi:
    """Thin async wrapper around the ControlMySpa REST API."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None

    async def async_login(self) -> None:
        """Exchange credentials for an access token."""
        payload = {"email": self._email, "password": self._password}
        try:
            async with self._session.post(
                f"{API_BASE}/auth/login", json=payload, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise ControlMySpaAuthError("Invalid credentials")
                resp.raise_for_status()
                body = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ControlMySpaConnectionError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise ControlMySpaConnectionError("timeout during login") from err

        try:
            self._token = body["data"]["accessToken"]
        except (KeyError, TypeError) as err:
            raise ControlMySpaAuthError("login response contained no token") from err

    async def _async_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        retry: bool = True,
    ) -> dict[str, Any]:
        """Perform an authenticated request, re-authenticating once on 401."""
        if self._token is None:
            await self.async_login()

        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with self._session.request(
                method,
                f"{API_BASE}{path}",
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401 and retry:
                    _LOGGER.debug("Token rejected, re-authenticating")
                    self._token = None
                    await self.async_login()
                    return await self._async_request(method, path, payload, retry=False)

                if resp.status == 401:
                    raise ControlMySpaAuthError("unauthorised after re-login")
                if resp.status == 204:
                    return {}
                resp.raise_for_status()
                if not resp.content_length:
                    return {}
                try:
                    return await resp.json(content_type=None)
                except ValueError:
                    return {}
        except aiohttp.ClientError as err:
            raise ControlMySpaConnectionError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise ControlMySpaConnectionError("request timed out") from err

    async def async_get_spas(self) -> list[dict[str, Any]]:
        """Return every spa owned by the account."""
        body = await self._async_request("GET", "/spas/owned")
        return body.get("data", {}).get("spas", []) or []

    async def async_get_dashboard(self, spa_id: str) -> dict[str, Any]:
        """Return the current dashboard payload for one spa."""
        body = await self._async_request("GET", f"/spas/{spa_id}/dashboard")
        return body.get("data", {}) or {}

    # ----------------------------------------------------------------- commands

    async def async_set_temperature(self, spa_id: str, value: float) -> None:
        """Set the target temperature. ``value`` is always Fahrenheit."""
        await self._async_request(
            "POST",
            "/spa-commands/temperature/value",
            {"value": value, "spaId": spa_id, "via": "MOBILE"},
        )

    async def async_set_temp_range(self, spa_id: str, high: bool) -> None:
        """Switch between the HIGH and LOW temperature range."""
        await self._async_request(
            "POST",
            "/spa-commands/temperature/range",
            {"range": "HIGH" if high else "LOW", "spaId": spa_id, "via": "MOBILE"},
        )

    async def async_set_heater_mode(self, spa_id: str, ready: bool) -> None:
        """Switch between READY (heat when needed) and REST (only on demand)."""
        await self._async_request(
            "POST",
            "/spa-commands/temperature/heater-mode",
            {"mode": "READY" if ready else "REST", "spaId": spa_id, "via": "MOBILE"},
        )

    async def async_set_panel_lock(self, spa_id: str, locked: bool) -> None:
        """Lock or unlock the physical panel."""
        await self._async_request(
            "POST",
            "/spa-commands/panel/state",
            {
                "state": "LOCK_PANEL" if locked else "UNLOCK_PANEL",
                "spaId": spa_id,
                "via": "MOBILE",
            },
        )

    async def async_set_component_state(
        self, spa_id: str, component_type: str, device_number: int, state: str
    ) -> None:
        """Set a component such as a pump, light or blower.

        ``component_type`` must be the lowercase command name the cloud expects
        (``jet``, ``light``, ``blower``) -- not the uppercase dashboard type.
        """
        await self._async_request(
            "POST",
            "/spa-commands/component-state",
            {
                "state": state,
                "deviceNumber": device_number,
                "componentType": component_type,
                "spaId": spa_id,
                "via": "MOBILE",
            },
        )
