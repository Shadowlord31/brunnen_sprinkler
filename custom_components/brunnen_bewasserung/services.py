from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import BrunnenBewasserungCoordinator

SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_SKIP_TODAY = "skip_today"
SERVICE_START_SEQUENCE = "start_sequence"
SERVICE_NOTIFY = "notify"

_SERVICE_SCHEMA = vol.Schema({
    vol.Optional("entry_id"): cv.string,
})

_NOTIFY_SCHEMA = vol.Schema({
    vol.Optional("entry_id"): cv.string,
    vol.Required("message"): cv.string,
    vol.Optional("title"): cv.string,
})


def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> BrunnenBewasserungCoordinator | None:
    entry_id = call.data.get("entry_id")
    domain_data: dict = hass.data.get(DOMAIN, {})

    if entry_id:
        return domain_data.get(entry_id)

    # Falls keine entry_id: erste verfügbare Instanz
    for coord in domain_data.values():
        return coord
    return None


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return

    async def handle_start(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        if coord:
            await coord.async_start_watering(force=True)

    async def handle_stop(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        if coord:
            await coord.async_stop_watering()

    async def handle_skip_today(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        if coord:
            await coord.async_skip_today()

    async def handle_start_sequence(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        if coord:
            await coord.async_start_watering(force=True)

    async def handle_notify(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        message = call.data["message"]
        title = call.data.get("title")
        if coord:
            await coord._async_notify(message=message, title=title)

    hass.services.async_register(DOMAIN, SERVICE_START, handle_start, schema=_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, handle_stop, schema=_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SKIP_TODAY, handle_skip_today, schema=_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_START_SEQUENCE, handle_start_sequence, schema=_SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_NOTIFY, handle_notify, schema=_NOTIFY_SCHEMA)
