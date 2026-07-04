from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN,
    CONF_INSTANCE_NAME, CONF_GARTEN_NAME,
    CONF_EARLIEST_START, DEFAULT_EARLIEST_START,
)
from .coordinator import GartenCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_GARTEN:
        return  # Frühestzeit gehört nur zum Garten
    coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GartenEarliestStartTime(coordinator, entry)])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_GARTEN_NAME, "Garten"),
        manufacturer="brunnen_bewasserung",
    )


class GartenEarliestStartTime(CoordinatorEntity[GartenCoordinator], TimeEntity):
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_earliest_start"
        self._attr_name = "Frühestzeit Start"
        self._attr_device_info = _device_info(entry)

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
