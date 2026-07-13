from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE, ENTRY_TYPE_MANUELL
from .coordinator import GartenCoordinator, BrunnenBewasserungCoordinator, ManuelleZoneCoordinator
from .services import async_register_services

PLATFORMS_ZONE = ["sensor", "binary_sensor", "switch", "number", "time", "button", "select"]
PLATFORMS_GARTEN = ["number", "time", "sensor", "binary_sensor", "switch"]
PLATFORMS_MANUELL = ["switch", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE)

    if entry_type == ENTRY_TYPE_GARTEN:
        coordinator = GartenCoordinator(hass, entry)
        await coordinator.async_setup()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_GARTEN)
        return True

    if entry_type == ENTRY_TYPE_MANUELL:
        coordinator = ManuelleZoneCoordinator(hass, entry)
        await coordinator.async_setup()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_MANUELL)
        return True

    coordinator = BrunnenBewasserungCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_ZONE)
    await async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE)
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_shutdown()
    if entry_type == ENTRY_TYPE_GARTEN:
        platforms = PLATFORMS_GARTEN
    elif entry_type == ENTRY_TYPE_MANUELL:
        platforms = PLATFORMS_MANUELL
    else:
        platforms = PLATFORMS_ZONE
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
