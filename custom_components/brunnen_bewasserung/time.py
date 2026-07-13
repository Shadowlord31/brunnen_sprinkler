from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE,
    CONF_INSTANCE_NAME, CONF_GARTEN_NAME,
    CONF_EARLIEST_START, DEFAULT_EARLIEST_START,
    CONF_ZONE_START_TIME, DEFAULT_ZONE_START_TIME,
)
from .coordinator import GartenCoordinator, BrunnenBewasserungCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([GartenEarliestStartTime(coordinator, entry)])
    elif entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_ZONE:
        coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([ZoneStartTime(coordinator, entry)])


def _garten_device(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_GARTEN_NAME, "Garten"),
        manufacturer="brunnen_bewasserung",
    )


def _zone_device(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Zone"),
        manufacturer="brunnen_bewasserung",
    )


class GartenEarliestStartTime(CoordinatorEntity[GartenCoordinator], TimeEntity):
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_earliest_start"
        self._attr_name = "Frühestzeit Start"
        self._attr_device_info = _garten_device(entry)

    @property
    def available(self): return True

    @property
    def native_value(self) -> time:
        val = self.coordinator.options.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)
        try:
            h, m = map(int, val.split(":"))
            return time(h, m)
        except Exception:
            return time(17, 30)

    async def async_set_value(self, value: time) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_EARLIEST_START] = value.strftime("%H:%M")
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()


class ZoneStartTime(CoordinatorEntity[BrunnenBewasserungCoordinator], TimeEntity):
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_zone_start_time"
        self._attr_name = "Startzeit"
        self._attr_device_info = _zone_device(entry)

    @property
    def available(self): return True

    @property
    def native_value(self) -> time | None:
        val = self.coordinator.options.get(CONF_ZONE_START_TIME, "")
        if not val:
            return None
        try:
            h, m = map(int, val.split(":"))
            return time(h, m)
        except Exception:
            return None

    async def async_set_value(self, value: time) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_ZONE_START_TIME] = value.strftime("%H:%M")
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        # Trigger-Zeit neu registrieren
        await self.coordinator._register_start_time_trigger()
        self.coordinator.async_update_listeners()
