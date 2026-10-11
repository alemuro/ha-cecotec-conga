"""Unit tests for Conga sensors and select entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.cecotec_conga.select import WATER_LEVELS, CongaWaterLevelSelect
from custom_components.cecotec_conga.sensor import SENSORS, CongaVacuumSensor


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {
        "status": {
            "cleanArea": 42,
            "allArea": 120,
            "cleanTime": 1500,  # 25 mins
            "allTime": 7200,   # 120 mins
            "elec": 80,
            "water": 2,
        },
        "plans": ["Pla1"],
    }
    coordinator.client = MagicMock()
    return coordinator


def test_sensor_values_and_unique_ids(mock_coordinator):
    for sensor_def in SENSORS:
        sensor = CongaVacuumSensor(mock_coordinator, "sn123", "Conga Pro", sensor_def)
        assert sensor.unique_id == f"sn123_{sensor_def['id']}"

        if sensor_def["id"] == "cleanArea":
            assert sensor.native_value == 42
        elif sensor_def["id"] == "cleanTime":
            assert sensor.native_value == 25  # 1500 / 60 rounded
        elif sensor_def["id"] == "allTime":
            assert sensor.native_value == 120
        elif sensor_def["id"] == "elec":
            assert sensor.native_value == 80


@pytest.mark.asyncio
async def test_select_water_level(mock_coordinator):
    select = CongaWaterLevelSelect(mock_coordinator, "sn123", "Conga Pro")
    assert select.unique_id == "sn123_water_level"
    assert select.current_option == WATER_LEVELS[2]  # index 2 -> "Medium"

    select.hass = MagicMock()
    select.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    mock_coordinator.async_request_refresh = AsyncMock()

    await select.async_select_option("High")
    mock_coordinator.client.set_water_level.assert_called_once_with("sn123", 3)
    mock_coordinator.async_request_refresh.assert_called_once()
