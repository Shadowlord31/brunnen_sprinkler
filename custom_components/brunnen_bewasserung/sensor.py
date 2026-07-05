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
)
from .coordinator import BrunnenBewasserungCoordinator, GartenCoordinator


def _zone_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_INSTANCE_NAME, "Zone"), manufacturer="brunnen_bewasserung")
def _garten_device(entry): return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.data.get(CONF_GARTEN_NAME, "Garten"), manufacturer="brunnen_bewasserung")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
        coordinator: GartenCoordinator = hass.data[DOMAIN][entry.entry_id]
        async_add_entities([GartenFlowCounterSensor(coordinator, entry)])
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
