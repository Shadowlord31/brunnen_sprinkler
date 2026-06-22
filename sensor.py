from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    CONF_NEXT_ZONE_ENTRY_ID,
    STATE_WATERING,
    STATE_PAUSING,
    STATE_WIND_HOLD,
    STATE_WAITING_WATER,
)
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BrunnenNextStartSensor(coordinator, entry),
        BrunnenRemainingTimeSensor(coordinator, entry),
        BrunnenStateSensor(coordinator, entry),
        BrunnenPauseModeSensor(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


class _BrunnenSensorBase(CoordinatorEntity[BrunnenBewasserungCoordinator], SensorEntity):

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return True


class BrunnenNextStartSensor(_BrunnenSensorBase):

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_start"
        self._attr_name = "Nächster Start"

    @property
    def native_value(self) -> str:
        return self.coordinator._get_next_start_info()


class BrunnenRemainingTimeSensor(_BrunnenSensorBase):

    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_remaining"
        self._attr_name = "Restzeit"

    @property
    def native_value(self) -> float:
        return round(self.coordinator.remaining_s / 60, 1)

    @property
    def extra_state_attributes(self) -> dict:
        coord = self.coordinator
        next_zone_title: str | None = None
        next_coord = coord._get_next_zone_coordinator()
        if next_coord:
            next_entry_id = coord.options.get(CONF_NEXT_ZONE_ENTRY_ID)
            next_entry = self.hass.config_entries.async_get_entry(next_entry_id) if next_entry_id else None
            if next_entry:
                next_zone_title = next_entry.title

        return {
            "remaining_seconds": coord.remaining_s,
            "current_block": coord.current_block,
            "total_blocks": coord.total_blocks,
            "pause_mode": coord.pause_mode,
            "next_zone": next_zone_title,
        }


class BrunnenStateSensor(_BrunnenSensorBase):

    _STATE_ICONS = {
        STATE_WATERING: "mdi:sprinkler-variant",
        STATE_PAUSING: "mdi:pause-circle",
        STATE_WIND_HOLD: "mdi:weather-windy",
        STATE_WAITING_WATER: "mdi:water-off",
    }
    _DEFAULT_ICON = "mdi:sleep"

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"
        self._attr_name = "Status"

    @property
    def native_value(self) -> str:
        return self.coordinator.state

    @property
    def icon(self) -> str:
        return self._STATE_ICONS.get(self.coordinator.state, self._DEFAULT_ICON)


class BrunnenPauseModeSensor(_BrunnenSensorBase):

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_pause_mode"
        self._attr_name = "Pause Modus"

    @property
    def native_value(self) -> str:
        return "Sensor" if self.coordinator.pause_mode == "sensor" else "Zeitbasiert"

    @property
    def icon(self) -> str:
        return "mdi:water-pump" if self.coordinator.pause_mode == "sensor" else "mdi:timer"
