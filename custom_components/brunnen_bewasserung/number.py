from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_INSTANCE_NAME, CONF_GARTEN_NAME,
    CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE,
    CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD,
    CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT,
    CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT,
    CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS,
    CONF_FLOW_IDLE_TIMEOUT, DEFAULT_FLOW_IDLE_TIMEOUT,
    CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION,
    CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION,
    CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME,
    CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME,
    CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME,
    CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE,
    CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT,
)
from .coordinator import BrunnenBewasserungCoordinator, GartenCoordinator


def _garten_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_GARTEN_NAME, "Garten"), manufacturer="brunnen_bewasserung")
def _zone_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_INSTANCE_NAME, "Zone"), manufacturer="brunnen_bewasserung")


class _NumberBase(CoordinatorEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, conf_key, name, unit, min_val, max_val, step, icon, default, entity_category=None, device_info=None):
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
        self._attr_device_info = device_info
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
    coordinator = hass.data[DOMAIN][entry.entry_id]

    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        di = _garten_device(entry)
        async_add_entities([
            _NumberBase(coordinator, entry, CONF_SOLAR_THRESHOLD, "Solar-Schwellwert", "W/m²", 50, 1000, 10, "mdi:weather-sunny", DEFAULT_SOLAR_THRESHOLD, device_info=di),
            _NumberBase(coordinator, entry, CONF_WIND_SPEED_LIMIT, "Max. Windgeschwindigkeit", "km/h", 5, 50, 1, "mdi:weather-windy", DEFAULT_WIND_SPEED_LIMIT, device_info=di),
            _NumberBase(coordinator, entry, CONF_WIND_GUST_LIMIT, "Max. Windböe", "km/h", 5, 80, 1, "mdi:weather-windy-variant", DEFAULT_WIND_GUST_LIMIT, device_info=di),
            _NumberBase(coordinator, entry, CONF_FLOW_PAUSE_LITERS, "Liter bis Brunnenpause", "L", 10, 2000, 10, "mdi:water-sync", DEFAULT_FLOW_PAUSE_LITERS, EntityCategory.CONFIG, di),
            _NumberBase(coordinator, entry, CONF_FLOW_IDLE_TIMEOUT, "Brunnen-Reset Timeout", "min", 5, 60, 5, "mdi:timer-refresh", DEFAULT_FLOW_IDLE_TIMEOUT, EntityCategory.CONFIG, di),
            _NumberBase(coordinator, entry, CONF_BLOCK_DURATION, "Block-Dauer", "min", 5, 60, 1, "mdi:clock-outline", DEFAULT_BLOCK_DURATION, device_info=di),
            _NumberBase(coordinator, entry, CONF_PAUSE_DURATION, "Pause-Dauer", "min", 5, 60, 1, "mdi:pause-circle-outline", DEFAULT_PAUSE_DURATION, device_info=di),
            _NumberBase(coordinator, entry, CONF_MIN_RUNTIME, "Minimale Laufzeit", "min", 1, 30, 1, "mdi:timer-minus", DEFAULT_MIN_RUNTIME, device_info=di),
            _NumberBase(coordinator, entry, CONF_MAX_RUNTIME, "Maximale Laufzeit", "min", 10, 180, 5, "mdi:timer-plus", DEFAULT_MAX_RUNTIME, device_info=di),
        ])
        return

    # Zone
    di = _zone_device(entry)
    entities = []
    has_moisture = bool(entry.data.get("moisture_sensor") or entry.options.get("moisture_sensor"))
    if has_moisture:
        entities += [
            _NumberBase(coordinator, entry, CONF_TARGET_MOISTURE, "Ziel-Bodenfeuchte", "%", 10, 100, 1, "mdi:water-percent", DEFAULT_TARGET_MOISTURE, device_info=di),
            _NumberBase(coordinator, entry, CONF_SECONDS_PER_PERCENT, "Sekunden pro Prozent", "s/%", 60, 600, 5, "mdi:timer", DEFAULT_SECONDS_PER_PERCENT, EntityCategory.CONFIG, di),
        ]
    else:
        entities.append(_NumberBase(coordinator, entry, CONF_FIXED_RUNTIME, "Feste Laufzeit", "min", 1, 180, 1, "mdi:timer", DEFAULT_FIXED_RUNTIME, device_info=di))
    async_add_entities(entities)
