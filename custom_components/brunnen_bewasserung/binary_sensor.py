from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_INSTANCE_NAME, CONF_GARTEN_NAME, CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_MANUELL, CONF_PARENT_ENTRY_ID,
    STATE_WATERING, STATE_PAUSING, STATE_WAITING_WATER, STATE_WIND_HOLD, STATE_WAITING_ZONE,
    STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE,
)
from .coordinator import BrunnenBewasserungCoordinator, GartenCoordinator, ManuelleZoneCoordinator


def _device_info(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_GARTEN_NAME) if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN else entry.data.get(CONF_INSTANCE_NAME, "Zone"), manufacturer="brunnen_bewasserung")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([GartenAktivSensor(coordinator, entry), GartenAutomatikAktivSensor(coordinator, entry)])
        return
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_MANUELL:
        coordinator: ManuelleZoneCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([
            ManuellAktivSensor(coordinator, entry),
            ManuellBrunnenpauseSensor(coordinator, entry),
        ])
        return
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ActiveSensor(coordinator, entry),
        PauseActiveSensor(coordinator, entry),
        WindHoldSensor(coordinator, entry),
    ])


class ActiveSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:sprinkler-variant"
    _attr_device_class = "running"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = "Bewässerung aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state in (STATE_WATERING, STATE_PAUSING, STATE_WAITING_WATER, STATE_WIND_HOLD)


class PauseActiveSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pause_active"
        self._attr_name = "Pause aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state in (STATE_PAUSING, STATE_WAITING_WATER)


class WindHoldSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:weather-windy"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wind_hold"
        self._attr_name = "Wind-Pause aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self): return self.coordinator.state == STATE_WIND_HOLD


class GartenAktivSensor(BinarySensorEntity):
    _attr_icon = "mdi:sprinkler-variant"
    _attr_device_class = "running"
    _attr_should_poll = False

    def __init__(self, coordinator: GartenCoordinator, entry):
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_bewasserung_aktiv"
        self._attr_name = "Bewässerung aktiv"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_GARTEN_NAME, "Garten"),
            manufacturer="brunnen_bewasserung",
        )
        self._unsubs = []

    async def async_added_to_hass(self) -> None:
        """Zonen-Koordinatoren abonnieren – mit Fallback-Polling."""
        from datetime import timedelta
        from homeassistant.helpers.event import async_track_time_interval

        def _update_subscriptions():
            """Neue Zonen-Koordinatoren finden und abonnieren."""
            for coord in self.hass.data.get(DOMAIN, {}).values():
                # Zonen-Coordinator hat CONF_PARENT_ENTRY_ID + _state
                if not hasattr(coord, '_state') or not hasattr(coord, 'options'):
                    continue
                if coord.options.get(CONF_PARENT_ENTRY_ID) == self._entry.entry_id:
                    if coord not in self._subscribed_coords:
                        self._subscribed_coords.add(coord)
                        self._unsubs.append(
                            coord.async_add_listener(self.async_write_ha_state)
                        )

        self._subscribed_coords = set()
        _update_subscriptions()

        # Alle 10s prüfen ob neue Zonen dazugekommen sind + State aktualisieren
        async def _tick(_now=None):
            _update_subscriptions()
            self.async_write_ha_state()

        self._unsubs.append(
            async_track_time_interval(
                self.hass, _tick, timedelta(seconds=10)
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @property
    def is_on(self) -> bool:
        return self._coordinator._any_zone_active()


class GartenAutomatikAktivSensor(BinarySensorEntity):
    """True wenn eine automatische Zone gerade bewaessert oder auf ihren Start wartet."""
    _attr_icon = "mdi:sprinkler-variant"
    _attr_device_class = "running"
    _attr_should_poll = False

    def __init__(self, coordinator: GartenCoordinator, entry):
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_automatik_aktiv"
        self._attr_name = "Automatik aktiv"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_GARTEN_NAME, "Garten"),
            manufacturer="brunnen_bewasserung",
        )
        self._unsubs = []

    async def async_added_to_hass(self) -> None:
        from datetime import timedelta
        from homeassistant.helpers.event import async_track_time_interval

        async def _tick(_now=None):
            self.async_write_ha_state()

        self._unsubs.append(
            async_track_time_interval(self.hass, _tick, timedelta(seconds=10))
        )

    async def async_will_remove_from_hass(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @property
    def is_on(self) -> bool:
        return self._coordinator.get_automatik_aktiv()


class ManuellAktivSensor(CoordinatorEntity[ManuelleZoneCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:valve-open"
    _attr_device_class = "running"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_aktiv"
        self._attr_name = "Aktiv"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator.state in (STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE)


class ManuellBrunnenpauseSensor(CoordinatorEntity[ManuelleZoneCoordinator], BinarySensorEntity):
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_brunnenpause"
        self._attr_name = "Brunnenpause"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        return self.coordinator.state == STATE_MANUELL_PAUSE
