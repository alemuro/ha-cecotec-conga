"""Unit tests for Cecotec Conga config flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.cecotec_conga.config_flow import CecotecCongaConfigFlow
from custom_components.cecotec_conga.const import CONF_PASSWORD, CONF_USERNAME


@pytest.fixture
def config_flow():
    flow = CecotecCongaConfigFlow()
    flow.hass = MagicMock()
    flow.hass.async_add_executor_job = AsyncMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_abort = MagicMock(return_value={"type": "abort"})
    return flow


@pytest.mark.asyncio
async def test_config_flow_success(config_flow):
    with patch("custom_components.cecotec_conga.config_flow.Conga") as mock_conga_class:
        mock_conga = MagicMock()
        mock_conga.list_vacuums.return_value = [{"sn": "12345", "note_name": "My Conga"}]
        mock_conga_class.return_value = mock_conga
        config_flow.hass.async_add_executor_job.side_effect = lambda func, *args: func(*args)

        result = await config_flow.async_step_user(
            {CONF_USERNAME: "test@example.com", CONF_PASSWORD: "secretpassword"}
        )

        assert result["type"] == "create_entry"
        config_flow.async_set_unique_id.assert_called_once_with("test@example.com")
        config_flow._abort_if_unique_id_configured.assert_called_once()
        config_flow.async_create_entry.assert_called_once()


@pytest.mark.asyncio
async def test_config_flow_auth_error(config_flow):
    with patch("custom_components.cecotec_conga.config_flow.Conga") as mock_conga_class:
        mock_conga = MagicMock()
        mock_conga.list_vacuums.side_effect = Exception("Invalid credentials")
        mock_conga_class.return_value = mock_conga
        config_flow.hass.async_add_executor_job.side_effect = lambda func, *args: func(*args)

        result = await config_flow.async_step_user(
            {CONF_USERNAME: "test@example.com", CONF_PASSWORD: "wrongpassword"}
        )

        assert result["type"] == "form"
        assert config_flow.async_show_form.call_args[1]["errors"]["base"] == "auth_error"
