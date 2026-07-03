from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_GARTEN_NAME,
    CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD,
    CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT,
    CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT,
    CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS,
)
from .coordinator import GartenCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_GARTEN_NAME, "Garten"),
        manufacturer="brunnen_bewasserung",
    )


class _GartenNumberBase(CoordinatorEntity[GartenCoordinator], NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, conf_key, name, unit, min_val, max_val, step, icon, default, entity_category=None):
        super().__init__(coordinator)
        self._entry = entry
        self._conf_key = conf_key
        self._default = default
        self._attr_unique_id = f"{entry.entry_id}_{conf_key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_icon = icon
        self._attr_device_info = _device_info(entry)
        if entity_category:
            self._attr_entity_category = entity_category

    @property
    def available(self): return True

    @property
    def native_value(self) -> float:
        return float(self.coordinator.options.get(self._conf_key, self._default))

    async def async_set_native_value(self, value: float) -> None:
        new_options = dict(self._entry.options)
        new_options[self._conf_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        _GartenNumberBase(coordinator, entry, CONF_SOLAR_THRESHOLD, "Solar-Schwellwert", "W/m²", 50, 1000, 10, "mdi:weather-sunny", DEFAULT_SOLAR_THRESHOLD),
        _GartenNumberBase(coordinator, entry, CONF_WIND_SPEED_LIMIT, "Max. Windgeschwindigkeit", "km/h", 5, 50, 1, "mdi:weather-windy", DEFAULT_WIND_SPEED_LIMIT),
        _GartenNumberBase(coordinator, entry, CONF_WIND_GUST_LIMIT, "Max. Windböe", "km/h", 5, 80, 1, "mdi:weather-windy-variant", DEFAULT_WIND_GUST_LIMIT),
        _GartenNumberBase(coordinator, entry, CONF_FLOW_PAUSE_LITERS, "Liter bis Brunnenpause", "L", 10, 2000, 10, "mdi:water-sync", DEFAULT_FLOW_PAUSE_LITERS, EntityCategory.CONFIG),
    ])
