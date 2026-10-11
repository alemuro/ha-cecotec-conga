"""Config flow for Cecotec Conga."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .conga import Conga
from .const import (
    CONF_DEVICES,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    STEP_LOGIN,
)

_LOGGER = logging.getLogger(__name__)


class CecotecCongaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Cecotec Conga config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_login(user_input)

    async def async_step_login(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle login step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            try:
                c = Conga(username, password)
                vacuums = await self.hass.async_add_executor_job(c.list_vacuums)

                return self.async_create_entry(
                    title=f"Cecotec Conga ({username})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_DEVICES: vacuums,
                    },
                )
            except Exception as err:
                _LOGGER.exception("Error validating Cecotec credentials: %s", err)
                errors["base"] = "auth_error"

        return self.async_show_form(
            step_id=STEP_LOGIN,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthorization request."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None

        if user_input is not None:
            username = self._reauth_entry.data[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                c = Conga(username, password)
                vacuums = await self.hass.async_add_executor_job(c.list_vacuums)

                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_PASSWORD: password,
                        CONF_DEVICES: vacuums,
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except Exception as err:
                _LOGGER.exception("Reauth failed for user %s: %s", username, err)
                errors["base"] = "auth_error"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={
                CONF_USERNAME: self._reauth_entry.data[CONF_USERNAME]
            },
            errors=errors,
        )
