"""Button Platform für brunnen_bewasserung."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrunnenResetLastRunButton(coordinator, entry)])


class BrunnenResetLastRunButton(ButtonEntity):

    _attr_icon = "mdi:calendar-refresh"
    _attr_has_entity_name = True

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset_last_run"
        self._attr_name = "Heute zurücksetzen"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(self.coordinator.reset_last_run)
