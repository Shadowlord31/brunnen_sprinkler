"""Switch Platform für brunnen_bewasserung – nur noch Status-Indikator."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTANCE_NAME, STATE_IDLE
from .coordinator import BrunnenBewasserungCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrunnenActiveSwitch(coordinator, entry)])


class BrunnenActiveSwitch(CoordinatorEntity[BrunnenBewasserungCoordinator], SwitchEntity):
    """
    Zeigt ob gerade bewässert wird (read-only Status).
    Tap startet/stoppt – funktioniert in allen Modi als Komfort-Toggle.
    """
    _attr_has_entity_name = True
    _attr_icon = "mdi:sprinkler"

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = "Bewässerung aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator._state != STATE_IDLE

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_start_watering(force=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_stop_watering()
