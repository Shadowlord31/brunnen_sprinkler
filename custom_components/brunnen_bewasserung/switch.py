from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTANCE_NAME
from .coordinator import BrunnenBewasserungCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BrunnenBewasserungCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BrunnenAutoModeSwitch(coordinator, entry),
        BrunnenEnabledSwitch(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung"),
        manufacturer="brunnen_bewasserung",
    )


class _BrunnenSwitchBase(CoordinatorEntity[BrunnenBewasserungCoordinator], SwitchEntity):

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return True


class BrunnenAutoModeSwitch(_BrunnenSwitchBase):

    _attr_icon = "mdi:auto-mode"

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_auto_mode"
        self._attr_name = "Automatikmodus"

    @property
    def is_on(self) -> bool:
        return self.coordinator.auto_mode

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator._auto_mode = True
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._auto_mode = False
        self.coordinator.async_update_listeners()


class BrunnenEnabledSwitch(_BrunnenSwitchBase):

    _attr_icon = "mdi:sprinkler"

    def __init__(self, coordinator: BrunnenBewasserungCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_enabled"
        self._attr_name = "Bewässerung aktiv"

    @property
    def is_on(self) -> bool:
        return self.coordinator.enabled

    async def async_turn_on(self, **kwargs) -> None:
        if not self.coordinator._auto_mode:
            # Manuell-Modus: sofortiger Start
            await self.coordinator.async_start_watering(force=True)
        else:
            self.coordinator._enabled = True
            self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._enabled = False
        await self.coordinator.async_stop_watering()
