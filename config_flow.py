"""Config flow for Desert Bus integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Desert Bus For Hope"

DATA_SCHEMA = vol.Schema(
    {
        ("subscribe_key"): str,
        ("channel"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> bool:
    return True


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Desert Bus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        # Assign a unique ID to the flow and abort the flow
        # if another flow with the same unique ID is in progress
        await self.async_set_unique_id("desert-bus-cloud")

        # Abort the flow if a config entry with the same unique ID exists
        self._abort_if_unique_id_configured()
        return await self.async_step_common(user_input)

    async def async_step_common(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """"""
        errors = {}
        if user_input is not None:
            try:
                data = await validate_input(self.hass, user_input)
                if data:
                    return self.async_create_entry(title=DEFAULT_NAME, data=user_input)
                else:
                    errors["base"] = "unable_validate"
            except Exception:
                errors["base"] = "error_validating"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of the receiver."""
        #return await self.async_step_common()
        errors = {}
        _LOGGER.debug("Reconfiguring desertbus")
        if user_input is not None:
            _LOGGER.debug("We have user input")
            try:
                _LOGGER.debug("validating user input")
                data = await validate_input(self.hass, user_input)
                if data:
                    _LOGGER.debug("Data validates")
                    await self.async_set_unique_id("desert-bus-cloud")
                    return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data=user_input)
                else:
                    _LOGGER.debug("Data DOES NOT validates")
                    errors["base"] = "unable_validate"
            except Exception:
                errors["base"] = "error_validating"

        return self.async_show_form(
            step_id="reconfigure", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_import(
        self, user_input: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)
