from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    STATE_WATERING,
    STATE_PAUSING,
    STATE_WIND_HOLD,
    STATE_WAITING_WATER,
)
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BrunnenIsWateringSensor(coordinator, entry),
        BrunnenIsPausingSensor(coordinator, entry),
        BrunnenIsWindHoldSensor(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


class _BrunnenBinarySensorBase(
    CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity
):
    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return True


class BrunnenIsWateringSensor(_BrunnenBinarySensorBase):

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_is_watering"
        self._attr_name = "Bewässerung aktiv"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state == STATE_WATERING


class BrunnenIsPausingSensor(_BrunnenBinarySensorBase):

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_is_pausing"
        self._attr_name = "Pause aktiv"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state in (STATE_PAUSING, STATE_WAITING_WATER)


class BrunnenIsWindHoldSensor(_BrunnenBinarySensorBase):

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_is_wind_hold"
        self._attr_name = "Wind-Pause aktiv"

    @property
    def is_on(self) -> bool:
        return self.coordinator.state == STATE_WIND_HOLD
