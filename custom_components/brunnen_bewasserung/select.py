from __future__ import annotations
# select.py - nicht mehr verwendet in v3.0 (Modus wurde durch Schalter ersetzt)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    pass
