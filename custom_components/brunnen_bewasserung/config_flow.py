from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector, EntitySelectorConfig,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    TextSelector, TimeSelector, BooleanSelector,
)

from .const import (
    DOMAIN,
    CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE,
    CONF_GARTEN_NAME, CONF_PARENT_ENTRY_ID, CONF_INSTANCE_NAME, CONF_PUMP_SWITCH,
    CONF_MAIN_PUMP_SWITCH, CONF_FLOW_SENSOR, CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS,
    CONF_FLOW_IDLE_TIMEOUT, DEFAULT_FLOW_IDLE_TIMEOUT,
    CONF_SOLAR_SENSOR, CONF_WIND_SPEED_SENSOR, CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT,
    CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT,
    CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD,
    CONF_EARLIEST_START, DEFAULT_EARLIEST_START,
    CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION,
    CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION,
    CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME,
    CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME,
    CONF_GIESS_ENABLED, CONF_GIESS_SENSOR,
    CONF_MOISTURE_SENSOR, CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE,
    CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT,
    CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME,
    CONF_AUTO_ENABLED, DEFAULT_AUTO_ENABLED,
    CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND,
    CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_ON_START, CONF_NOTIFY_ON_FINISH, CONF_NOTIFY_ON_BLOCK_PAUSE,
    CONF_NOTIFY_ON_STOP, CONF_NOTIFY_ON_WIND, CONF_NOTIFY_ON_NO_WATER_NEEDED,
    DEFAULT_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_BLOCK_PAUSE,
    DEFAULT_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED,
)

_N = NumberSelectorConfig
_NM = NumberSelectorMode


class BrunnenBewasserungConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return await self.async_step_garten() if user_input["type"] == "garten" else await self.async_step_zone()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("type", default="zone"): SelectSelector(SelectSelectorConfig(options=[
                    {"value": "garten", "label": "🌿 Garten anlegen"},
                    {"value": "zone", "label": "💧 Zone hinzufügen"},
                ], mode=SelectSelectorMode.LIST)),
            }),
        )

    async def async_step_garten(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            self._data[CONF_ENTRY_TYPE] = ENTRY_TYPE_GARTEN
            return self.async_create_entry(title=f"🌿 {user_input.get(CONF_GARTEN_NAME, 'Garten')}", data=self._data)
        return self.async_show_form(step_id="garten", data_schema=vol.Schema({
            vol.Required(CONF_GARTEN_NAME, default="Garten"): TextSelector(),
            vol.Required(CONF_SOLAR_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_WIND_SPEED_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_WIND_GUST_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_EARLIEST_START, default=DEFAULT_EARLIEST_START): TimeSelector(),
            vol.Required(CONF_WIND_SPEED_LIMIT, default=DEFAULT_WIND_SPEED_LIMIT): NumberSelector(_N(min=5, max=50, step=1, unit_of_measurement="km/h", mode=_NM.BOX)),
            vol.Required(CONF_WIND_GUST_LIMIT, default=DEFAULT_WIND_GUST_LIMIT): NumberSelector(_N(min=5, max=80, step=1, unit_of_measurement="km/h", mode=_NM.BOX)),
            vol.Required(CONF_SOLAR_THRESHOLD, default=DEFAULT_SOLAR_THRESHOLD): NumberSelector(_N(min=50, max=1000, step=10, unit_of_measurement="W/m²", mode=_NM.BOX)),
            vol.Required(CONF_BLOCK_DURATION, default=DEFAULT_BLOCK_DURATION): NumberSelector(_N(min=5, max=60, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_PAUSE_DURATION, default=DEFAULT_PAUSE_DURATION): NumberSelector(_N(min=5, max=60, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_MIN_RUNTIME, default=DEFAULT_MIN_RUNTIME): NumberSelector(_N(min=1, max=30, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_MAX_RUNTIME, default=DEFAULT_MAX_RUNTIME): NumberSelector(_N(min=10, max=180, step=5, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Optional(CONF_MAIN_PUMP_SWITCH): EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
            vol.Required(CONF_FLOW_PAUSE_LITERS, default=DEFAULT_FLOW_PAUSE_LITERS): NumberSelector(_N(min=10, max=2000, step=10, unit_of_measurement="L", mode=_NM.BOX)),
            vol.Required(CONF_FLOW_IDLE_TIMEOUT, default=DEFAULT_FLOW_IDLE_TIMEOUT): NumberSelector(_N(min=5, max=60, step=5, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_GIESS_ENABLED, default=True): BooleanSelector(),
            vol.Optional(CONF_GIESS_SENSOR): EntitySelector(EntitySelectorConfig(domain=["sensor", "binary_sensor", "input_boolean"])),
        }))

    async def async_step_zone(self, user_input=None):
        errors = {}
        garten_entries = [e for e in self.hass.config_entries.async_entries(DOMAIN) if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN]
        if not garten_entries:
            errors["base"] = "no_garten"
        if user_input is not None and not errors:
            self._data.update(user_input)
            self._data[CONF_ENTRY_TYPE] = ENTRY_TYPE_ZONE
            return await self.async_step_zone_settings()
        garten_options = [{"value": e.entry_id, "label": e.data.get(CONF_GARTEN_NAME, e.entry_id)} for e in garten_entries]
        return self.async_show_form(step_id="zone", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_PARENT_ENTRY_ID): SelectSelector(SelectSelectorConfig(options=garten_options, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_INSTANCE_NAME, default="Zone"): TextSelector(),
            vol.Required(CONF_PUMP_SWITCH): EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
            vol.Optional(CONF_MOISTURE_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_FLOW_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_AUTO_ENABLED, default=DEFAULT_AUTO_ENABLED): BooleanSelector(),
            vol.Required(CONF_IGNORE_WIND, default=DEFAULT_IGNORE_WIND): BooleanSelector(),
        }))

    async def async_step_zone_settings(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=f"💧 {self._data.get(CONF_INSTANCE_NAME, 'Zone')}", data=self._data)
        has_moisture = bool(self._data.get(CONF_MOISTURE_SENSOR))
        fields = {vol.Optional(CONF_NOTIFY_SERVICE): EntitySelector(EntitySelectorConfig(domain=["notify", "script"]))}
        if has_moisture:
            fields[vol.Required(CONF_TARGET_MOISTURE, default=DEFAULT_TARGET_MOISTURE)] = NumberSelector(_N(min=10, max=100, step=1, unit_of_measurement="%", mode=_NM.BOX))
            fields[vol.Required(CONF_SECONDS_PER_PERCENT, default=DEFAULT_SECONDS_PER_PERCENT)] = NumberSelector(_N(min=60, max=600, step=5, unit_of_measurement="s/%", mode=_NM.BOX))
        else:
            fields[vol.Required(CONF_FIXED_RUNTIME, default=DEFAULT_FIXED_RUNTIME)] = NumberSelector(_N(min=1, max=180, step=1, unit_of_measurement="min", mode=_NM.BOX))
        return self.async_show_form(step_id="zone_settings", data_schema=vol.Schema(fields))

    @staticmethod
    def async_get_options_flow(config_entry):
        return BrunnenOptionsFlow()


class BrunnenOptionsFlow(config_entries.OptionsFlow):

    def __init__(self):
        self._data: dict = {}

    async def async_step_init(self, user_input=None):
        self._data = {**self.config_entry.data, **self.config_entry.options}
        if self._data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN:
            return await self.async_step_garten(user_input)
        return await self.async_step_zone(user_input)

    async def async_step_garten(self, user_input=None):
        d = self._data
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications_garten()
        return self.async_show_form(step_id="garten", data_schema=vol.Schema({
            vol.Required(CONF_EARLIEST_START, default=d.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)): TimeSelector(),
            vol.Required(CONF_WIND_SPEED_LIMIT, default=d.get(CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT)): NumberSelector(_N(min=5, max=50, step=1, unit_of_measurement="km/h", mode=_NM.BOX)),
            vol.Required(CONF_WIND_GUST_LIMIT, default=d.get(CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT)): NumberSelector(_N(min=5, max=80, step=1, unit_of_measurement="km/h", mode=_NM.BOX)),
            vol.Required(CONF_SOLAR_THRESHOLD, default=d.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD)): NumberSelector(_N(min=50, max=1000, step=10, unit_of_measurement="W/m²", mode=_NM.BOX)),
            vol.Required(CONF_BLOCK_DURATION, default=d.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)): NumberSelector(_N(min=5, max=60, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_PAUSE_DURATION, default=d.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION)): NumberSelector(_N(min=5, max=60, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_MIN_RUNTIME, default=d.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME)): NumberSelector(_N(min=1, max=30, step=1, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_MAX_RUNTIME, default=d.get(CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME)): NumberSelector(_N(min=10, max=180, step=5, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Required(CONF_FLOW_PAUSE_LITERS, default=d.get(CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS)): NumberSelector(_N(min=10, max=2000, step=10, unit_of_measurement="L", mode=_NM.BOX)),
            vol.Required(CONF_FLOW_IDLE_TIMEOUT, default=d.get(CONF_FLOW_IDLE_TIMEOUT, DEFAULT_FLOW_IDLE_TIMEOUT)): NumberSelector(_N(min=5, max=60, step=5, unit_of_measurement="min", mode=_NM.BOX)),
            vol.Optional(CONF_MAIN_PUMP_SWITCH): EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
            vol.Required(CONF_GIESS_ENABLED, default=d.get(CONF_GIESS_ENABLED, True)): BooleanSelector(),
            vol.Optional(CONF_GIESS_SENSOR): EntitySelector(EntitySelectorConfig(domain=["sensor", "binary_sensor", "input_boolean"])),
        }))

    async def async_step_notifications_garten(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        return self.async_show_form(step_id="notifications_garten", data_schema=vol.Schema({}))

    async def async_step_zone(self, user_input=None):
        d = self._data
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_zone_settings()
        garten_entries = [e for e in self.hass.config_entries.async_entries(DOMAIN) if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN]
        garten_options = [{"value": e.entry_id, "label": e.data.get(CONF_GARTEN_NAME, e.entry_id)} for e in garten_entries]
        next_zone_options = [{"value": "", "label": "– keine –"}] + [
            {"value": e.entry_id, "label": e.data.get(CONF_INSTANCE_NAME, e.entry_id)}
            for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_ZONE and e.entry_id != self.config_entry.entry_id
        ]
        return self.async_show_form(step_id="zone", data_schema=vol.Schema({
            vol.Optional(CONF_MOISTURE_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Optional(CONF_FLOW_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_AUTO_ENABLED, default=d.get(CONF_AUTO_ENABLED, DEFAULT_AUTO_ENABLED)): BooleanSelector(),
            vol.Required(CONF_IGNORE_WIND, default=d.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND)): BooleanSelector(),
            vol.Optional(CONF_NOTIFY_SERVICE): EntitySelector(EntitySelectorConfig(domain=["notify", "script"])),
        }))

    async def async_step_zone_settings(self, user_input=None):
        d = self._data
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()
        has_moisture = bool(d.get(CONF_MOISTURE_SENSOR))
        fields = {}
        if has_moisture:
            fields[vol.Required(CONF_TARGET_MOISTURE, default=d.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))] = NumberSelector(_N(min=10, max=100, step=1, unit_of_measurement="%", mode=_NM.BOX))
            fields[vol.Required(CONF_SECONDS_PER_PERCENT, default=d.get(CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT))] = NumberSelector(_N(min=60, max=600, step=5, unit_of_measurement="s/%", mode=_NM.BOX))
        else:
            fields[vol.Required(CONF_FIXED_RUNTIME, default=d.get(CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME))] = NumberSelector(_N(min=1, max=180, step=1, unit_of_measurement="min", mode=_NM.BOX))
        if not fields:
            return await self.async_step_notifications()
        return self.async_show_form(step_id="zone_settings", data_schema=vol.Schema(fields))

    async def async_step_notifications(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        d = self._data
        return self.async_show_form(step_id="notifications", data_schema=vol.Schema({
            vol.Required(CONF_NOTIFY_ON_START, default=d.get(CONF_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_START)): BooleanSelector(),
            vol.Required(CONF_NOTIFY_ON_FINISH, default=d.get(CONF_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_FINISH)): BooleanSelector(),
            vol.Required(CONF_NOTIFY_ON_BLOCK_PAUSE, default=d.get(CONF_NOTIFY_ON_BLOCK_PAUSE, DEFAULT_NOTIFY_ON_BLOCK_PAUSE)): BooleanSelector(),
            vol.Required(CONF_NOTIFY_ON_STOP, default=d.get(CONF_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_STOP)): BooleanSelector(),
            vol.Required(CONF_NOTIFY_ON_WIND, default=d.get(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND)): BooleanSelector(),
            vol.Required(CONF_NOTIFY_ON_NO_WATER_NEEDED, default=d.get(CONF_NOTIFY_ON_NO_WATER_NEEDED, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED)): BooleanSelector(),
        }))
