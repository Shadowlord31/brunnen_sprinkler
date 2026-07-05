from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTANCE_NAME, CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE
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
    async_add_entities([AutomatikSwitch(coordinator, entry)])


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
