from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTANCE_NAME, CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE, CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND
from .coordinator import BrunnenBewasserungCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Zone"),
        manufacturer="brunnen_bewasserung",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_ZONE:
        return
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutomatikSwitch(coordinator, entry), WindIgnoreSwitch(coordinator, entry)])


class AutomatikSwitch(CoordinatorEntity[BrunnenBewasserungCoordinator], SwitchEntity):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_auto_enabled"
        self._attr_name = "Automatik"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator.auto_enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_enabled(False)


class WindIgnoreSwitch(CoordinatorEntity[BrunnenBewasserungCoordinator], SwitchEntity):
    _attr_icon = "mdi:weather-windy-variant"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ignore_wind"
        self._attr_name = "Windpause ignorieren"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        opts = dict(self._entry.data)
        opts.update(self._entry.options)
        return bool(opts.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND))

    async def async_turn_on(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_IGNORE_WIND] = True
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_IGNORE_WIND] = False
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()
