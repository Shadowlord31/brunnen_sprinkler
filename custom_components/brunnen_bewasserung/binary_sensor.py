from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_INSTANCE_NAME, CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE,
    STATE_WATERING, STATE_MANUAL, STATE_PAUSING, STATE_WAITING_WATER, STATE_WIND_HOLD,
)
from .coordinator import BrunnenBewasserungCoordinator


def _device_info(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_INSTANCE_NAME, "Zone"), manufacturer="brunnen_bewasserung")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_ZONE:
        return
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ActiveSensor(coordinator, entry),
        PauseActiveSensor(coordinator, entry),
        WindHoldSensor(coordinator, entry),
    ])


class ActiveSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:sprinkler-variant"
    _attr_device_class = "running"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = "Bewässerung aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state in (STATE_WATERING, STATE_MANUAL)


class PauseActiveSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pause_active"
        self._attr_name = "Pause aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state in (STATE_PAUSING, STATE_WAITING_WATER)


class WindHoldSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:weather-windy"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wind_hold"
        self._attr_name = "Wind-Pause aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state == STATE_WIND_HOLD
