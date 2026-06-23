"""Select Platform für brunnen_bewasserung – Bewässerungsmodus."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, CONF_INSTANCE_NAME,
    MODE_AUTO, MODE_CHAIN, MODE_MANUAL, CONF_MODE,
)
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrunnenModusSelect(coordinator, entry)])


class BrunnenModusSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:list-box"
    _attr_options = [MODE_AUTO, MODE_CHAIN, MODE_MANUAL]
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BrunnenBewasserungCoordinator,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_modus"
        self._attr_name = "Modus"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
            manufacturer="brunnen_bewasserung",
        )

    @property
    def current_option(self) -> str:
        return self._coordinator.mode

    async def async_select_option(self, option: str) -> None:
        self._coordinator._mode = option
        # In options persistieren
        new_options = dict(self._entry.options)
        new_options[CONF_MODE] = option
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self._coordinator.async_update_listeners()

    async def async_added_to_hass(self) -> None:
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        pass
