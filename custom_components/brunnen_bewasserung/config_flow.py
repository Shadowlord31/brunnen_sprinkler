from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TimeSelector,
    BooleanSelector,
)

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    CONF_PUMP_SWITCH,
    CONF_MOISTURE_SENSOR,
    CONF_SOLAR_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_GIESS_ENABLED,
    CONF_GIESS_SENSOR,
    CONF_NEXT_ZONE_ENTRY_ID,
    CONF_WATER_LEVEL_SENSOR,
    CONF_WATER_LEVEL_LOW,
    CONF_WATER_LEVEL_HIGH,
    CONF_WATER_LEVEL_TIMEOUT,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_TITLE,
    DEFAULT_NOTIFY_TITLE,
    CONF_TARGET_MOISTURE,
    CONF_SECONDS_PER_PERCENT,
    CONF_MIN_RUNTIME,
    CONF_MAX_RUNTIME,
    CONF_BLOCK_DURATION,
    CONF_PAUSE_DURATION,
    CONF_WIND_SPEED_LIMIT,
    CONF_WIND_GUST_LIMIT,
    CONF_SOLAR_THRESHOLD,
    CONF_EARLIEST_START,
    DEFAULT_TARGET_MOISTURE,
    DEFAULT_SECONDS_PER_PERCENT,
    DEFAULT_MIN_RUNTIME,
    DEFAULT_MAX_RUNTIME,
    DEFAULT_BLOCK_DURATION,
    DEFAULT_PAUSE_DURATION,
    DEFAULT_WIND_SPEED_LIMIT,
    DEFAULT_WIND_GUST_LIMIT,
    DEFAULT_SOLAR_THRESHOLD,
    DEFAULT_EARLIEST_START,
    DEFAULT_WATER_LEVEL_LOW,
    DEFAULT_WATER_LEVEL_HIGH,
    DEFAULT_WATER_LEVEL_TIMEOUT,
)


def _settings_schema(defaults: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TARGET_MOISTURE, default=defaults.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE)):
            NumberSelector(NumberSelectorConfig(min=10, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_SECONDS_PER_PERCENT, default=defaults.get(CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT)):
            NumberSelector(NumberSelectorConfig(min=60, max=600, step=5, unit_of_measurement="s/%", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_MIN_RUNTIME, default=defaults.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME)):
            NumberSelector(NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_MAX_RUNTIME, default=defaults.get(CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME)):
            NumberSelector(NumberSelectorConfig(min=10, max=180, step=5, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_BLOCK_DURATION, default=defaults.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)):
            NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_PAUSE_DURATION, default=defaults.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION)):
            NumberSelector(NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_WIND_SPEED_LIMIT, default=defaults.get(CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT)):
            NumberSelector(NumberSelectorConfig(min=5, max=50, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_WIND_GUST_LIMIT, default=defaults.get(CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT)):
            NumberSelector(NumberSelectorConfig(min=5, max=80, step=1, unit_of_measurement="km/h", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_SOLAR_THRESHOLD, default=defaults.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD)):
            NumberSelector(NumberSelectorConfig(min=50, max=1000, step=10, unit_of_measurement="W/m²", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_EARLIEST_START, default=defaults.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)):
            TimeSelector(),
        vol.Optional(CONF_NOTIFY_SERVICE):
            EntitySelector(EntitySelectorConfig(domain=["notify", "script"])),
        vol.Optional(CONF_NOTIFY_TITLE, default=defaults.get(CONF_NOTIFY_TITLE, DEFAULT_NOTIFY_TITLE)):
            TextSelector(TextSelectorConfig(autocomplete="off")),
    })


def _optional_sensors_schema(hass, defaults: dict, own_entry_id: str | None = None) -> vol.Schema:
    other_entries = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != own_entry_id
    ]
    next_zone_options = [{"value": "", "label": "— keine —"}] + [
        {"value": e.entry_id, "label": e.title} for e in other_entries
    ]

    return vol.Schema({
        vol.Optional(CONF_NEXT_ZONE_ENTRY_ID, default=defaults.get(CONF_NEXT_ZONE_ENTRY_ID) or ""):
            SelectSelector(SelectSelectorConfig(
                options=next_zone_options,
                mode=SelectSelectorMode.DROPDOWN,
            )),
        vol.Optional(CONF_WATER_LEVEL_SENSOR, default=defaults.get(CONF_WATER_LEVEL_SENSOR) or ""):
            TextSelector(TextSelectorConfig(autocomplete="off")),
        vol.Required(CONF_WATER_LEVEL_LOW, default=defaults.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)):
            NumberSelector(NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_WATER_LEVEL_HIGH, default=defaults.get(CONF_WATER_LEVEL_HIGH, DEFAULT_WATER_LEVEL_HIGH)):
            NumberSelector(NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=NumberSelectorMode.BOX)),
        vol.Required(CONF_WATER_LEVEL_TIMEOUT, default=defaults.get(CONF_WATER_LEVEL_TIMEOUT, DEFAULT_WATER_LEVEL_TIMEOUT)):
            NumberSelector(NumberSelectorConfig(min=5, max=120, step=5, unit_of_measurement="min", mode=NumberSelectorMode.BOX)),
    })


class BrunnenBewasserungConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            required_entities = [
                user_input[CONF_PUMP_SWITCH],
                user_input[CONF_MOISTURE_SENSOR],
                user_input[CONF_SOLAR_SENSOR],
                user_input[CONF_WIND_SPEED_SENSOR],
                user_input[CONF_WIND_GUST_SENSOR],
            ]
            for entity_id in required_entities:
                if not self.hass.states.get(entity_id):
                    errors["base"] = "entity_not_found"
                    break

            if not errors:
                self._data.update(user_input)
                return await self.async_step_optional_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_INSTANCE_NAME, default="Garten"):
                    TextSelector(),
                vol.Required(CONF_PUMP_SWITCH):
                    EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"])),
                vol.Required(CONF_MOISTURE_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_SOLAR_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_WIND_SPEED_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_WIND_GUST_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_GIESS_ENABLED, default=True):
                    BooleanSelector(),
                vol.Optional(CONF_GIESS_SENSOR):
                    EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
            }),
            errors=errors,
        )

    async def async_step_optional_sensors(self, user_input=None):
        errors = {}

        if user_input is not None:
            low = user_input.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)
            high = user_input.get(CONF_WATER_LEVEL_HIGH, DEFAULT_WATER_LEVEL_HIGH)
            if low >= high:
                errors["base"] = "water_level_invalid"

            if not errors:
                # Leere Strings in None umwandeln
                for key in (CONF_NEXT_ZONE_ENTRY_ID, CONF_WATER_LEVEL_SENSOR):
                    if user_input.get(key, "") == "":
                        user_input[key] = None
                self._data.update(user_input)
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="optional_sensors",
            data_schema=_optional_sensors_schema(self.hass, self._data),
            errors=errors,
        )

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            instance_name = self._data.get(CONF_INSTANCE_NAME, "Garten")
            return self.async_create_entry(
                title=f"Brunnen Bewässerung – {instance_name}",
                data=self._data,
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self._data),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return BrunnenBewasserungOptionsFlow(config_entry)


class BrunnenBewasserungOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        # Merge: data als Basis, options überschreiben (persistierte Änderungen)
        self._data: dict = {**config_entry.data, **config_entry.options}

    async def async_step_init(self, user_input=None):
        return await self.async_step_optional_sensors(user_input)

    async def async_step_optional_sensors(self, user_input=None):
        errors = {}

        if user_input is not None:
            low = user_input.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)
            high = user_input.get(CONF_WATER_LEVEL_HIGH, DEFAULT_WATER_LEVEL_HIGH)
            if low >= high:
                errors["base"] = "water_level_invalid"

            if not errors:
                for key in (CONF_NEXT_ZONE_ENTRY_ID, CONF_WATER_LEVEL_SENSOR):
                    if user_input.get(key, "") == "":
                        user_input[key] = None
                self._data.update(user_input)
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="optional_sensors",
            data_schema=_optional_sensors_schema(self.hass, self._data, self._entry.entry_id),
            errors=errors,
        )

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self._data),
        )
