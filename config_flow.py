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
        errors = {}
        if self._async_current_entries():
            errors["base"] = "single_instance_allowed"
        elif user_input is not None:
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

    async def async_step_import(
        self, user_input: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)
