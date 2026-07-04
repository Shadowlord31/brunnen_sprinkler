from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector, EntitySelectorConfig,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    TextSelector, TextSelectorConfig,
    TimeSelector, BooleanSelector,
)

from .const import (
    DOMAIN,
    CONF_ENTRY_TYPE, ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE,
    CONF_GARTEN_NAME, CONF_PARENT_ENTRY_ID,
    CONF_INSTANCE_NAME, CONF_PUMP_SWITCH,
    CONF_MAIN_PUMP_SWITCH, CONF_FLOW_SENSOR,
    CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS,
    CONF_SOLAR_SENSOR, CONF_WIND_SPEED_SENSOR, CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_LIMIT, CONF_WIND_GUST_LIMIT,
    DEFAULT_WIND_SPEED_LIMIT, DEFAULT_WIND_GUST_LIMIT,
    CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD,
    CONF_EARLIEST_START, DEFAULT_EARLIEST_START,
    CONF_MODE, DEFAULT_MODE,
    CONF_CHAIN_POSITION, DEFAULT_CHAIN_POSITION,
    CONF_MANUAL_DURATION, DEFAULT_MANUAL_DURATION,
    CONF_MANUAL_USE_TIMER, DEFAULT_MANUAL_USE_TIMER,
    CONF_MOISTURE_SENSOR,
    CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE,
    CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT,
    CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME,
    CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME,
    CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME,
    CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION,
    CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION,
    CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK,
    CONF_GIESS_ENABLED, CONF_GIESS_SENSOR,
    CONF_NEXT_ZONE_ENTRY_ID,
    CONF_NOTIFY_SERVICE, CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE,
    CONF_NOTIFY_ON_START, CONF_NOTIFY_ON_FINISH, CONF_NOTIFY_ON_BLOCK_PAUSE,
    CONF_NOTIFY_ON_STOP, CONF_NOTIFY_ON_WIND,
    CONF_NOTIFY_ON_NEXT_ZONE, CONF_NOTIFY_ON_NO_WATER_NEEDED,
    DEFAULT_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_BLOCK_PAUSE,
    DEFAULT_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_WIND,
    DEFAULT_NOTIFY_ON_NEXT_ZONE, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED,
    MODE_AUTO, MODE_CHAIN, MODE_MANUAL,
)


class BrunnenBewasserungConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Erster Schritt: Garten oder Zone?"""
        if user_input is not None:
            choice = user_input.get("type")
            if choice == "garten":
                return await self.async_step_garten()
            else:
                return await self.async_step_zone()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("type", default="zone"): SelectSelector(SelectSelectorConfig(
                    options=[
                        {"value": "garten", "label": "🌿 Garten anlegen (Wetterstation, Pumpe, Durchfluss)"},
                        {"value": "zone", "label": "💧 Zone hinzufügen (Ventil, Laufzeit, Modus)"},
                    ],
                    mode=SelectSelectorMode.LIST,
                )),
            }),
        )

    # === GARTEN FLOW ===

    async def async_step_garten(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            self._data[CONF_ENTRY_TYPE] = ENTRY_TYPE_GARTEN
            return self.async_create_entry(
                title=f"🌿 {user_input.get(CONF_GARTEN_NAME, 'Garten')}",
                data=self._data,
            )

        return self.async_show_form(
            step_id="garten",
            data_schema=vol.Schema({
                vol.Required(CONF_GARTEN_NAME, default="Garten"):
                    TextSelector(),
                vol.Required(CONF_SOLAR_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_WIND_SPEED_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_WIND_GUST_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_EARLIEST_START, default=DEFAULT_EARLIEST_START):
                    TimeSelector(),
                vol.Required(CONF_WIND_SPEED_LIMIT, default=DEFAULT_WIND_SPEED_LIMIT):
                    NumberSelector(NumberSelectorConfig(min=5, max=50, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_WIND_GUST_LIMIT, default=DEFAULT_WIND_GUST_LIMIT):
                    NumberSelector(NumberSelectorConfig(min=5, max=80, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_SOLAR_THRESHOLD, default=DEFAULT_SOLAR_THRESHOLD):
                    NumberSelector(NumberSelectorConfig(min=50, max=1000, step=10, unit_of_measurement="W/m²", mode=NumberSelectorMode.BOX)),
                vol.Optional(CONF_MAIN_PUMP_SWITCH):
                    EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
                vol.Optional(CONF_FLOW_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_FLOW_PAUSE_LITERS, default=DEFAULT_FLOW_PAUSE_LITERS):
                    NumberSelector(NumberSelectorConfig(min=10, max=2000, step=10, unit_of_measurement="L", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_GIESS_ENABLED, default=True):
                    BooleanSelector(),
                vol.Optional(CONF_GIESS_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain=["sensor", "binary_sensor", "input_boolean"])),
            }),
            errors=errors,
        )

    # === ZONE FLOW ===

    async def async_step_zone(self, user_input=None):
        errors = {}

        # Vorhandene Gärten ermitteln
        garten_entries = [
            e for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_GARTEN
        ]

        if not garten_entries:
            errors["base"] = "no_garten"

        if user_input is not None and not errors:
            self._data.update(user_input)
            self._data[CONF_ENTRY_TYPE] = ENTRY_TYPE_ZONE
            return await self.async_step_zone_settings()

        garten_options = [
            {"value": e.entry_id, "label": e.data.get(CONF_GARTEN_NAME, e.entry_id)}
            for e in garten_entries
        ]

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema({
                vol.Required(CONF_PARENT_ENTRY_ID):
                    SelectSelector(SelectSelectorConfig(
                        options=garten_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )),
                vol.Required(CONF_INSTANCE_NAME, default="Zone"):
                    TextSelector(),
                vol.Required(CONF_PUMP_SWITCH):
                    EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
                vol.Optional(CONF_MOISTURE_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
            }),
            errors=errors,
        )

    async def async_step_zone_settings(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            name = self._data.get(CONF_INSTANCE_NAME, "Zone")
            return self.async_create_entry(
                title=f"💧 {name}",
                data=self._data,
            )

        has_moisture = bool(self._data.get(CONF_MOISTURE_SENSOR))

        schema_fields = {
            vol.Required(CONF_MODE, default=DEFAULT_MODE):
                SelectSelector(SelectSelectorConfig(
                    options=[MODE_AUTO, MODE_CHAIN, MODE_MANUAL],
                    mode=SelectSelectorMode.DROPDOWN,
                )),
            vol.Required(CONF_BLOCK_DURATION, default=DEFAULT_BLOCK_DURATION):
                NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_PAUSE_DURATION, default=DEFAULT_PAUSE_DURATION):
                NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_MANUAL_USE_TIMER, default=DEFAULT_MANUAL_USE_TIMER):
                BooleanSelector(),
            vol.Required(CONF_MANUAL_DURATION, default=DEFAULT_MANUAL_DURATION):
                NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_CHAIN_POSITION, default=DEFAULT_CHAIN_POSITION):
                NumberSelector(NumberSelectorConfig(min=1, max=20, step=1, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_NOTIFY_SERVICE):
                EntitySelector(EntitySelectorConfig(domain=["notify", "script"])),
        }

        if has_moisture:
            schema_fields[vol.Required(CONF_TARGET_MOISTURE, default=DEFAULT_TARGET_MOISTURE)] =                 NumberSelector(NumberSelectorConfig(min=10, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_SECONDS_PER_PERCENT, default=DEFAULT_SECONDS_PER_PERCENT)] =                 NumberSelector(NumberSelectorConfig(min=60, max=600, step=5, unit_of_measurement="s/%", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_MIN_RUNTIME, default=DEFAULT_MIN_RUNTIME)] =                 NumberSelector(NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_MAX_RUNTIME, default=DEFAULT_MAX_RUNTIME)] =                 NumberSelector(NumberSelectorConfig(min=10, max=180, step=5, unit_of_measurement="min", mode=NumberSelectorMode.BOX))
        else:
            schema_fields[vol.Required(CONF_FIXED_RUNTIME, default=DEFAULT_FIXED_RUNTIME)] =                 NumberSelector(NumberSelectorConfig(min=1, max=180, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX))

        return self.async_show_form(
            step_id="zone_settings",
            data_schema=vol.Schema(schema_fields),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return BrunnenBewasserungOptionsFlow()


class BrunnenBewasserungOptionsFlow(config_entries.OptionsFlow):

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_init(self, user_input=None):
        self._data = {**self.config_entry.data, **self.config_entry.options}
        entry_type = self._data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_ZONE)
        if entry_type == ENTRY_TYPE_GARTEN:
            return await self.async_step_garten(user_input)
        return await self.async_step_zone(user_input)

    async def async_step_garten(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="garten",
            data_schema=vol.Schema({
                vol.Required(CONF_EARLIEST_START, default=self._data.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)):
                    TimeSelector(),
                vol.Required(CONF_WIND_SPEED_LIMIT, default=self._data.get(CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT)):
                    NumberSelector(NumberSelectorConfig(min=5, max=50, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_WIND_GUST_LIMIT, default=self._data.get(CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT)):
                    NumberSelector(NumberSelectorConfig(min=5, max=80, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_SOLAR_THRESHOLD, default=self._data.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD)):
                    NumberSelector(NumberSelectorConfig(min=50, max=1000, step=10, unit_of_measurement="W/m²", mode=NumberSelectorMode.BOX)),
                vol.Required(CONF_FLOW_PAUSE_LITERS, default=self._data.get(CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS)):
                    NumberSelector(NumberSelectorConfig(min=10, max=2000, step=10, unit_of_measurement="L", mode=NumberSelectorMode.BOX)),
                vol.Optional(CONF_MAIN_PUMP_SWITCH):
                    EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
                vol.Optional(CONF_FLOW_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_GIESS_ENABLED, default=self._data.get(CONF_GIESS_ENABLED, True)):
                    BooleanSelector(),
                vol.Optional(CONF_GIESS_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain=["sensor", "binary_sensor", "input_boolean"])),
            }),
        )

    async def async_step_zone(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_zone_settings()

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema({
                vol.Optional(CONF_MOISTURE_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_NEXT_ZONE_ENTRY_ID):
                    SelectSelector(SelectSelectorConfig(
                        options=[{"value": "", "label": "– keine –"}] + [
                            {"value": e.entry_id, "label": e.data.get(CONF_INSTANCE_NAME, e.entry_id)}
                            for e in self.hass.config_entries.async_entries(DOMAIN)
                            if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_ZONE and e.entry_id != self.config_entry.entry_id
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )),
            }),
        )

    async def async_step_zone_settings(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notifications()

        has_moisture = bool(self._data.get(CONF_MOISTURE_SENSOR))
        schema_fields = {
            vol.Required(CONF_MODE, default=self._data.get(CONF_MODE, DEFAULT_MODE)):
                SelectSelector(SelectSelectorConfig(options=[MODE_AUTO, MODE_CHAIN, MODE_MANUAL], mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_BLOCK_DURATION, default=self._data.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)):
                NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_PAUSE_DURATION, default=self._data.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION)):
                NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_MANUAL_USE_TIMER, default=self._data.get(CONF_MANUAL_USE_TIMER, DEFAULT_MANUAL_USE_TIMER)):
                BooleanSelector(),
            vol.Required(CONF_MANUAL_DURATION, default=self._data.get(CONF_MANUAL_DURATION, DEFAULT_MANUAL_DURATION)):
                NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_CHAIN_POSITION, default=self._data.get(CONF_CHAIN_POSITION, DEFAULT_CHAIN_POSITION)):
                NumberSelector(NumberSelectorConfig(min=1, max=20, step=1, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_NOTIFY_SERVICE):
                EntitySelector(EntitySelectorConfig(domain=["notify", "script"])),
        }

        if has_moisture:
            schema_fields[vol.Required(CONF_TARGET_MOISTURE, default=self._data.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))] =                 NumberSelector(NumberSelectorConfig(min=10, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_SECONDS_PER_PERCENT, default=self._data.get(CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT))] =                 NumberSelector(NumberSelectorConfig(min=60, max=600, step=5, unit_of_measurement="s/%", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_MIN_RUNTIME, default=self._data.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME))] =                 NumberSelector(NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX))
            schema_fields[vol.Required(CONF_MAX_RUNTIME, default=self._data.get(CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME))] =                 NumberSelector(NumberSelectorConfig(min=10, max=180, step=5, unit_of_measurement="min", mode=NumberSelectorMode.BOX))
        else:
            schema_fields[vol.Required(CONF_FIXED_RUNTIME, default=self._data.get(CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME))] =                 NumberSelector(NumberSelectorConfig(min=1, max=180, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX))

        return self.async_show_form(step_id="zone_settings", data_schema=vol.Schema(schema_fields))

    async def async_step_notifications(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema({
                vol.Required(CONF_NOTIFY_ON_START, default=self._data.get(CONF_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_START)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_FINISH, default=self._data.get(CONF_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_FINISH)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_BLOCK_PAUSE, default=self._data.get(CONF_NOTIFY_ON_BLOCK_PAUSE, DEFAULT_NOTIFY_ON_BLOCK_PAUSE)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_STOP, default=self._data.get(CONF_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_STOP)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_WIND, default=self._data.get(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_NEXT_ZONE, default=self._data.get(CONF_NOTIFY_ON_NEXT_ZONE, DEFAULT_NOTIFY_ON_NEXT_ZONE)): BooleanSelector(),
                vol.Required(CONF_NOTIFY_ON_NO_WATER_NEEDED, default=self._data.get(CONF_NOTIFY_ON_NO_WATER_NEEDED, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED)): BooleanSelector(),
            }),
        )
