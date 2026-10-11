"""Unit tests for CongaVacuum."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.vacuum import VacuumActivity

from custom_components.cecotec_conga.vacuum import (
    EVENT_CODE_CHARGING,
    EVENT_CODE_CLEANING,
    FAN_SPEEDS,
    WATER_LEVELS,
    CongaVacuum,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {
        "status": {
            "mode": "sweep",
            "eventCode": EVENT_CODE_CLEANING,
            "workNoisy": 1,
            "elec": 85,
        },
        "plans": ["Cuina", "Menjador"],
    }
    coordinator.client = MagicMock()
    return coordinator


def test_vacuum_properties(mock_coordinator):
    vacuum = CongaVacuum(mock_coordinator, "12345", "Conga Pro")
    assert vacuum.name == "Conga Pro"
    assert vacuum.unique_id == "12345"
    assert vacuum.fan_speed == FAN_SPEEDS[1]
    assert vacuum.fan_speed_list == FAN_SPEEDS
    assert vacuum.extra_state_attributes["Serial Number"] == "12345"
    assert vacuum.extra_state_attributes["plans"] == "Cuina,Menjador"


def test_vacuum_activity_resolution(mock_coordinator):
    vacuum = CongaVacuum(mock_coordinator, "12345", "Conga Pro")

    # Actively cleaning (sweep + 6023)
    mock_coordinator.data["status"] = {"mode": "sweep", "eventCode": EVENT_CODE_CLEANING}
    assert vacuum.activity == VacuumActivity.CLEANING

    # Docked with residual sweep mode (sweep + 6096)
    mock_coordinator.data["status"] = {"mode": "sweep", "eventCode": EVENT_CODE_CHARGING}
    assert vacuum.activity == VacuumActivity.DOCKED

    # Returning
    mock_coordinator.data["status"] = {"mode": "backcharge"}
    assert vacuum.activity == VacuumActivity.RETURNING
    mock_coordinator.data["status"] = {"mode": "DustCenterWorking"}
    assert vacuum.activity == VacuumActivity.RETURNING

    # DOCKED
    mock_coordinator.data["status"] = {"mode": "charge"}
    assert vacuum.activity == VacuumActivity.DOCKED
    mock_coordinator.data["status"] = {"mode": "fullcharge"}
    assert vacuum.activity == VacuumActivity.DOCKED

    # PAUSED
    mock_coordinator.data["status"] = {"mode": "pause"}
    assert vacuum.activity == VacuumActivity.PAUSED

    # IDLE
    mock_coordinator.data["status"] = {"mode": "idle"}
    assert vacuum.activity == VacuumActivity.IDLE
    mock_coordinator.data["status"] = {"mode": "shutdown"}
    assert vacuum.activity == VacuumActivity.IDLE

    # UNKNOWN
    mock_coordinator.data["status"] = {"mode": "alien_state"}
    assert vacuum.activity == VacuumActivity.ERROR


@pytest.mark.asyncio
async def test_vacuum_async_commands(mock_coordinator):
    vacuum = CongaVacuum(mock_coordinator, "12345", "Conga Pro")
    vacuum.hass = MagicMock()
    vacuum.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    mock_coordinator.async_request_refresh = AsyncMock()

    # Turn on
    await vacuum.async_turn_on()
    mock_coordinator.client.start.assert_called_once_with("12345", 1)
    mock_coordinator.async_request_refresh.assert_called_once()

    # Return home
    mock_coordinator.async_request_refresh.reset_mock()
    await vacuum.async_return_to_base()
    mock_coordinator.client.home.assert_called_once_with("12345")
    mock_coordinator.async_request_refresh.assert_called_once()

    # Set fan speed
    mock_coordinator.async_request_refresh.reset_mock()
    await vacuum.async_set_fan_speed(FAN_SPEEDS[2])
    mock_coordinator.client.set_fan_speed.assert_called_once_with("12345", 2)

    # Start plan service
    mock_coordinator.async_request_refresh.reset_mock()
    await vacuum.async_start_plan("Cuina")
    mock_coordinator.client.start_plan.assert_called_once_with("12345", "Cuina")

    # Set water level service
    mock_coordinator.async_request_refresh.reset_mock()
    await vacuum.async_set_water_level(WATER_LEVELS[2])
    mock_coordinator.client.set_water_level.assert_called_once_with("12345", 2)
