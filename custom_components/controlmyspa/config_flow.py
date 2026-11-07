"""Config flow for ControlMySpa."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import ControlMySpaApi, ControlMySpaAuthError, ControlMySpaError
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SPA_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _spa_label(spa: dict[str, Any]) -> str:
    """Human-readable label: the spa's own name, otherwise its serial."""
    alias = (spa.get("alias") or "").strip()
    serial = (spa.get("serialNumber") or spa.get("_id") or "").strip()
    if alias and serial:
        return f"{alias} ({serial})"
    return alias or serial


class ControlMySpaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in once, then tick the spas you want in Home Assistant."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._password: str = ""
        self._spas: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect account credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            api = ControlMySpaApi(
                async_get_clientsession(self.hass), email, user_input[CONF_PASSWORD]
            )
            try:
                await api.async_login()
                spas = await api.async_get_spas()
            except ControlMySpaAuthError:
                errors["base"] = "invalid_auth"
            except ControlMySpaError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - never leak a traceback into the UI
                _LOGGER.exception("Unexpected error during ControlMySpa setup")
                errors["base"] = "unknown"
            else:
                if not spas:
                    errors["base"] = "no_spas"
                else:
                    await self.async_set_unique_id(email.lower())
                    self._abort_if_unique_id_configured()
                    self._email = email
                    self._password = user_input[CONF_PASSWORD]
                    self._spas = spas
                    if len(spas) == 1:
                        return self._async_create_entry_for([spas[0]["_id"]], spas[0])
                    return await self.async_step_spa()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_spa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user tick which spas to add."""
        if user_input is not None:
            selected = user_input.get(CONF_SPA_IDS) or []
            if selected:
                first = next(
                    (s for s in self._spas if s["_id"] == selected[0]), self._spas[0]
                )
                return self._async_create_entry_for(selected, first)

        options = [
            SelectOptionDict(value=spa["_id"], label=_spa_label(spa)) for spa in self._spas
        ]
        return self.async_show_form(
            step_id="spa",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SPA_IDS, default=[opt["value"] for opt in options]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    def _async_create_entry_for(
        self, spa_ids: list[str], primary: dict[str, Any]
    ) -> ConfigFlowResult:
        """Create one entry holding every selected spa."""
        title = _spa_label(primary)
        if len(spa_ids) > 1:
            title = f"ControlMySpa ({len(spa_ids)} spas)"
        return self.async_create_entry(
            title=title,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_SPA_IDS: spa_ids,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password again after an auth failure."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None and entry is not None:
            api = ControlMySpaApi(
                async_get_clientsession(self.hass),
                entry.data[CONF_EMAIL],
                user_input[CONF_PASSWORD],
            )
            try:
                await api.async_login()
            except ControlMySpaAuthError:
                errors["base"] = "invalid_auth"
            except ControlMySpaError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={
                "email": entry.data.get(CONF_EMAIL, "") if entry else ""
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return ControlMySpaOptionsFlow()


class ControlMySpaOptionsFlow(OptionsFlow):
    """Polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=3600,
                            step=10,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
