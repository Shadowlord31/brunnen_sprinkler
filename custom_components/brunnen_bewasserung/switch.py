from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTANCE_NAME, CONF_GARTEN_NAME, CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_MANUELL, CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND, CONF_AUTO_PUMP_OFF, DEFAULT_AUTO_PUMP_OFF, STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE
from .coordinator import BrunnenBewasserungCoordinator, GartenCoordinator, ManuelleZoneCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    name = entry.data.get(CONF_GARTEN_NAME) if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN else entry.data.get(CONF_INSTANCE_NAME, "Zone")
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=name,
        manufacturer="brunnen_bewasserung",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([AutoPumpOffSwitch(coordinator, entry)])
        return
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_MANUELL:
        coordinator: ManuelleZoneCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([ManuellVentilSwitch(coordinator, entry)])
        return
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutomatikSwitch(coordinator, entry), WindIgnoreSwitch(coordinator, entry)])


class ManuellVentilSwitch(CoordinatorEntity[ManuelleZoneCoordinator], SwitchEntity):
    _attr_icon = "mdi:valve"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_manuell"
        self._attr_name = "Ventil"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator.state in (STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_open()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_close()


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


class AutoPumpOffSwitch(CoordinatorEntity[GartenCoordinator], SwitchEntity):
    _attr_icon = "mdi:pump"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_auto_pump_off"
        self._attr_name = "Pumpe automatisch ausschalten"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        opts = dict(self._entry.data)
        opts.update(self._entry.options)
        return bool(opts.get(CONF_AUTO_PUMP_OFF, DEFAULT_AUTO_PUMP_OFF))

    async def async_turn_on(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_AUTO_PUMP_OFF] = True
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs) -> None:
        new_options = dict(self._entry.options)
        new_options[CONF_AUTO_PUMP_OFF] = False
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.coordinator.async_update_listeners()
