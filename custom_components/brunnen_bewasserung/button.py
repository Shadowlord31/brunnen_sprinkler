"""Button Platform für brunnen_bewasserung."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_INSTANCE_NAME
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrunnenResetLastRunButton(coordinator, entry)])


class BrunnenResetLastRunButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-refresh"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BrunnenBewasserungCoordinator,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_reset_last_run"
        self._attr_name = "Heute zurücksetzen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
            manufacturer="brunnen_bewasserung",
        )

    async def async_press(self) -> None:
        await self._coordinator.async_reset_last_run()
