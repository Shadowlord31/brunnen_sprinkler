from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    CONF_TARGET_MOISTURE,
    CONF_SECONDS_PER_PERCENT,
    CONF_MIN_RUNTIME,
    CONF_MAX_RUNTIME,
    CONF_BLOCK_DURATION,
    CONF_PAUSE_DURATION,
    CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME,
    DEFAULT_TARGET_MOISTURE,
    DEFAULT_SECONDS_PER_PERCENT,
    DEFAULT_MIN_RUNTIME,
    DEFAULT_MAX_RUNTIME,
    DEFAULT_BLOCK_DURATION,
    DEFAULT_PAUSE_DURATION,
    CONF_MANUAL_DURATION, DEFAULT_MANUAL_DURATION,
    CONF_CHAIN_POSITION, DEFAULT_CHAIN_POSITION,
    MODE_CHAIN, CONF_MODE,
)
from .coordinator import BrunnenBewasserungCoordinator





class _BrunnenNumberBase(CoordinatorEntity[BrunnenBewasserungCoordinator], NumberEntity):
    """Abstrakte Basisklasse fuer Number-Entities mit conf_key/default Pattern."""

    _attr_mode = NumberMode.BOX
    _conf_key: str
    _default: float

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return float(self.coordinator.options.get(self._conf_key, self._default))

    async def async_set_native_value(self, value: float) -> None:
        new_options = dict(self._entry.options)
        new_options[self._conf_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()

class BrunnenManualDurationNumber(_BrunnenNumberBase):
    """Konfigurierbare Laufzeit im Manuell-Modus."""
    _attr_icon = "mdi:timer-play-outline"
    _attr_native_min_value = 1.0
    _attr_native_max_value = 120.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._conf_key = CONF_MANUAL_DURATION
        self._default = DEFAULT_MANUAL_DURATION
        self._attr_unique_id = f"{entry.entry_id}_manual_duration"
        self._attr_name = "Manuelle Laufzeit"


class BrunnenChainPositionNumber(_BrunnenNumberBase):
    """Kettenposition – bestimmt die Reihenfolge im Ketten-Modus."""
    _attr_icon = "mdi:sort-numeric-ascending"
    _attr_native_min_value = 1.0
    _attr_native_max_value = 20.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._conf_key = CONF_CHAIN_POSITION
        self._default = DEFAULT_CHAIN_POSITION
        self._attr_unique_id = f"{entry.entry_id}_chain_position"
        self._attr_name = "Kettenposition"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BrunnenNumber(coordinator, entry, CONF_TARGET_MOISTURE, "Ziel-Bodenfeuchte", "%", 10, 100, 1, "mdi:water-percent", DEFAULT_TARGET_MOISTURE),
        BrunnenNumber(coordinator, entry, CONF_SECONDS_PER_PERCENT, "Sekunden pro Prozent", "s/%", 60, 600, 5, "mdi:timer-sand", DEFAULT_SECONDS_PER_PERCENT),
        BrunnenNumber(coordinator, entry, CONF_MIN_RUNTIME, "Minimale Laufzeit", "min", 1, 30, 1, "mdi:timer-outline", DEFAULT_MIN_RUNTIME),
        BrunnenNumber(coordinator, entry, CONF_MAX_RUNTIME, "Maximale Laufzeit", "min", 10, 180, 5, "mdi:timer-outline", DEFAULT_MAX_RUNTIME),
        BrunnenNumber(coordinator, entry, CONF_BLOCK_DURATION, "Block-Dauer", "min", 5, 60, 1, "mdi:timer-play", DEFAULT_BLOCK_DURATION, entity_category=EntityCategory.CONFIG),
        BrunnenNumber(coordinator, entry, CONF_PAUSE_DURATION, "Pause-Dauer", "min", 5, 60, 1, "mdi:timer-pause", DEFAULT_PAUSE_DURATION, entity_category=EntityCategory.CONFIG),
            BrunnenManualDurationNumber(coordinator, entry),
        BrunnenChainPositionNumber(coordinator, entry),
        BrunnenNumber(coordinator, entry, CONF_FIXED_RUNTIME, "Feste Laufzeit", "min", 1, 180, 1, "mdi:timer", DEFAULT_FIXED_RUNTIME, entity_category=EntityCategory.CONFIG),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


class BrunnenNumber(CoordinatorEntity[BrunnenBewasserungCoordinator], NumberEntity):

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BrunnenBewasserungCoordinator,
        entry: ConfigEntry,
        conf_key: str,
        name: str,
        unit: str,
        min_val: float,
        max_val: float,
        step: float,
        icon: str,
        default: float,
        entity_category: EntityCategory | None = None,
    ) -> None:
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
        if entity_category is not None:
            self._attr_entity_category = entity_category

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return float(self.coordinator.options.get(self._conf_key, self._default))

    async def async_set_native_value(self, value: float) -> None:
        new_options = dict(self._entry.options)
        new_options[self._conf_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()
