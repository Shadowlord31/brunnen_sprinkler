"""Button Platform für brunnen_bewasserung."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_INSTANCE_NAME, MODE_MANUAL
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BrunnenStartButton(coordinator, entry),
        BrunnenStopButton(coordinator, entry),
        BrunnenResetLastRunButton(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


class BrunnenStartButton(ButtonEntity):
    """Startet die Bewässerung – in allen Modi nutzbar."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:play-circle"
    _attr_should_poll = False

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_start"
        self._attr_name = "Start"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_start_watering(force=True)


class BrunnenStopButton(ButtonEntity):
    """Stoppt die Bewässerung sofort."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:stop-circle"
    _attr_should_poll = False

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_stop"
        self._attr_name = "Stop"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_stop_watering()


class BrunnenResetLastRunButton(ButtonEntity):
    """Setzt den Tagesstand zurück."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-refresh"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_reset_last_run"
        self._attr_name = "Heute zurücksetzen"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self._coordinator.async_reset_last_run()
