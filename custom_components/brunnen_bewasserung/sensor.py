from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, CONF_INSTANCE_NAME, CONF_GARTEN_NAME,
    CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE, ENTRY_TYPE_GARTEN,
    STATE_MANUELL_OPEN,
)
from .coordinator import BrunnenBewasserungCoordinator, GartenCoordinator


def _zone_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_INSTANCE_NAME, "Zone"), manufacturer="brunnen_bewasserung")
def _garten_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_GARTEN_NAME, "Garten"), manufacturer="brunnen_bewasserung")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([
            GartenFlowCounterSensor(coordinator, entry),
            GartenManuellOffenSensor(coordinator, entry),
            GartenBrunnenpauseRestzeitSensor(coordinator, entry),
        ])
        return
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        StatusSensor(coordinator, entry),
        RestSensor(coordinator, entry),
        NextStartSensor(coordinator, entry),
        EtappeSensor(coordinator, entry),
    ])


class GartenFlowCounterSensor(CoordinatorEntity[GartenCoordinator], SensorEntity):
    _attr_icon = "mdi:water-pump"
    _attr_native_unit_of_measurement = "L"
    _attr_device_class = "water"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_flow_counter"
        self._attr_name = "Brunnen Zähler"
        self._attr_device_info = _garten_device(entry)

    @property
    def native_value(self):
        return round(self.coordinator.flow_counter, 1)


class GartenManuellOffenSensor(SensorEntity):
    """Anzahl aktuell geoeffneter Manuell-Zonen dieses Gartens."""
    _attr_icon = "mdi:valve-open"
    _attr_should_poll = False

    def __init__(self, coordinator: GartenCoordinator, entry):
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_manuell_offen"
        self._attr_name = "Manuell offen"
        self._attr_device_info = _garten_device(entry)
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
    def native_value(self):
        return sum(1 for z in self._coordinator.get_open_zones() if z.state == STATE_MANUELL_OPEN)

    @property
    def extra_state_attributes(self):
        names = [
            z.options.get(CONF_INSTANCE_NAME, "Manuell")
            for z in self._coordinator.get_open_zones() if z.state == STATE_MANUELL_OPEN
        ]
        return {"zonen": names}


class GartenBrunnenpauseRestzeitSensor(SensorEntity):
    """Restzeit der aktuell laufenden Brunnenpause (laengste unter allen Zonen dieses Gartens)."""
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "min"
    _attr_should_poll = False

    def __init__(self, coordinator: GartenCoordinator, entry):
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_brunnenpause_restzeit"
        self._attr_name = "Brunnenpause Restzeit"
        self._attr_device_info = _garten_device(entry)
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
    def native_value(self):
        return round(self._coordinator.get_pause_remaining_s() / 60, 1)


class StatusSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], SensorEntity):
    _attr_icon = "mdi:information"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = "Status"
        self._attr_device_info = _zone_device(entry)

    @property
    def native_value(self): return self.coordinator.state


class RestSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], SensorEntity):
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_restzeit"
        self._attr_name = "Restzeit"
        self._attr_device_info = _zone_device(entry)

    @property
    def native_value(self):
        return round(self.coordinator.remaining_s / 60, 1)


class NextStartSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], SensorEntity):
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_start"
        self._attr_name = "Nächster Start"
        self._attr_device_info = _zone_device(entry)

    @property
    def native_value(self): return self.coordinator._get_next_start_info()


class EtappeSensor(CoordinatorEntity[BrunnenBewasserungCoordinator], SensorEntity):
    _attr_icon = "mdi:timer"
    _attr_native_unit_of_measurement = "s"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_etappe"
        self._attr_name = "Aktuelle Etappe"
        self._attr_device_info = _zone_device(entry)

    @property
    def native_value(self): return round(self.coordinator.block_remaining_s, 2)
    
    @property
    def extra_state_attributes(self):
        c = self.coordinator
        return {"block": c.current_block, "total_blocks": c.total_blocks}
