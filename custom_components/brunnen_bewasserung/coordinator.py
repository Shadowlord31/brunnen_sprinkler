from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from math import ceil
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now

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
    STATE_IDLE,
    STATE_WATERING,
    STATE_PAUSING,
    STATE_WIND_HOLD,
    STATE_WAITING_WATER,
)

_LOGGER = logging.getLogger(__name__)

from datetime import timedelta
_CHECK_INTERVAL = timedelta(minutes=5)


class BrunnenBewasserungCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self._config_entry = config_entry
        self._state: str = STATE_IDLE
        self._remaining_s: float = 0.0
        self._block_remaining_s: float = 0.0
        self._current_block: int = 0
        self._total_blocks: int = 0
        self._last_run: date | None = None
        self._auto_mode: bool = True
        self._enabled: bool = True
        self._pause_mode: str = "time"
        self._watering_task: asyncio.Task | None = None
        self._water_level_unsub: Callable | None = None
        self._wind_unsub: Callable | None = None
        self._time_unsub: Callable | None = None

    # --- Properties ---

    @property
    def state(self) -> str:
        return self._state

    @property
    def remaining_s(self) -> float:
        return self._remaining_s

    @property
    def block_remaining_s(self) -> float:
        return self._block_remaining_s

    @property
    def current_block(self) -> int:
        return self._current_block

    @property
    def total_blocks(self) -> int:
        return self._total_blocks

    @property
    def last_run(self) -> date | None:
        return self._last_run

    @property
    def auto_mode(self) -> bool:
        return self._auto_mode

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def pause_mode(self) -> str:
        return self._pause_mode

    @property
    def options(self) -> dict:
        # Merge data + options; options overwrite data (OptionsFlow schreibt in options)
        merged = dict(self._config_entry.data)
        merged.update(self._config_entry.options)
        return merged

    # --- Setup / Teardown ---

    async def async_setup(self) -> bool:
        opts = self.options
        self._pause_mode = "sensor" if self._has_water_level_sensor() else "time"

        wind_entities = [
            opts.get(CONF_WIND_SPEED_SENSOR),
            opts.get(CONF_WIND_GUST_SENSOR),
        ]
        self._wind_unsub = async_track_state_change_event(
            self.hass, wind_entities, self._async_check_wind
        )

        self._time_unsub = async_track_time_interval(
            self.hass, self._async_background_check, _CHECK_INTERVAL
        )

        water_sensor = opts.get(CONF_WATER_LEVEL_SENSOR)
        if water_sensor:
            self._water_level_unsub = async_track_state_change_event(
                self.hass, [water_sensor], self._async_water_level_changed
            )

        return True

    async def async_shutdown(self) -> None:
        for unsub in (self._wind_unsub, self._time_unsub, self._water_level_unsub):
            if unsub:
                unsub()
        self._wind_unsub = None
        self._time_unsub = None
        self._water_level_unsub = None
        await self.async_stop_watering()

    # --- Public API ---

    async def async_start_watering(self, force: bool = False) -> bool:
        if self._state != STATE_IDLE:
            return False
        if not self._enabled:
            return False

        runtime_s = self._calculate_runtime()
        if runtime_s <= 0:
            await self._async_notify(message="Bodenfeuchte bereits ausreichend – keine Bewässerung nötig.")
            return False

        if not force and self._last_run == date.today():
            return False

        self._pause_mode = "sensor" if self._has_water_level_sensor() else "time"
        opts = self.options
        block_s = min(runtime_s, opts.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION) * 60)
        self._total_blocks = ceil(runtime_s / block_s)
        self._current_block = 1
        self._remaining_s = runtime_s - block_s
        self._last_run = date.today()
        self._watering_task = self.hass.async_create_task(
            self._async_run_watering_cycle(block_s)
        )
        return True

    async def async_stop_watering(self) -> None:
        if self._watering_task:
            self._watering_task.cancel()
            self._watering_task = None
        await self._async_pump_off()
        self._state = STATE_IDLE
        self._remaining_s = 0.0
        self._block_remaining_s = 0.0
        self._current_block = 0
        self.async_update_listeners()

    async def async_skip_today(self) -> None:
        self._last_run = date.today()
        self.async_update_listeners()

    # --- Watering Cycle ---

    async def _async_run_watering_cycle(self, first_block_s: float) -> None:
        opts = self.options
        block_duration_s = opts.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION) * 60
        current_block_s = first_block_s

        try:
            while True:
                self._state = STATE_WATERING
                self.async_update_listeners()
                await self._async_pump_on()

                await self._async_run_block(current_block_s)

                await self._async_pump_off()
                self.async_update_listeners()

                if self._remaining_s <= 0:
                    self._state = STATE_IDLE
                    self._current_block = 0
                    self.async_update_listeners()
                    await self._async_notify(message="Bewässerung abgeschlossen.")
                    await self._async_trigger_next_zone()
                    break

                if self._pause_mode == "sensor":
                    await self._async_run_pause_sensor()
                else:
                    await self._async_run_pause_time()

                # Falls stop_watering während Pause aufgerufen wurde
                if self._state == STATE_IDLE:
                    break

                self._current_block += 1
                next_block_s = min(self._remaining_s, block_duration_s)
                self._remaining_s -= next_block_s
                current_block_s = next_block_s

        except asyncio.CancelledError:
            pass

    async def _async_run_block(self, duration_s: float) -> None:
        self._block_remaining_s = duration_s
        step = 1.0
        elapsed = 0.0
        while elapsed < duration_s:
            await asyncio.sleep(step)
            elapsed += step
            self._block_remaining_s = max(0.0, duration_s - elapsed)

    async def _async_run_pause_time(self) -> None:
        opts = self.options
        pause_s = opts.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION) * 60
        self._state = STATE_PAUSING
        self.async_update_listeners()
        await self._async_notify(
            message=f"Block {self._current_block}/{self._total_blocks} beendet. "
                    f"Pause {int(pause_s // 60)} Min. Restzeit: {self._remaining_s / 60:.0f} Min."
        )
        await asyncio.sleep(pause_s)

    async def _async_run_pause_sensor(self) -> None:
        opts = self.options
        low = opts.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)
        high = opts.get(CONF_WATER_LEVEL_HIGH, DEFAULT_WATER_LEVEL_HIGH)
        timeout_s = opts.get(CONF_WATER_LEVEL_TIMEOUT, DEFAULT_WATER_LEVEL_TIMEOUT) * 60
        sensor = opts.get(CONF_WATER_LEVEL_SENSOR)

        self._state = STATE_WAITING_WATER
        self.async_update_listeners()
        await self._async_notify(
            message=f"Wasserstand niedrig. Warte auf Erholung (Ziel: >{high}%)."
        )

        start = datetime.now()
        while True:
            try:
                state_obj = self.hass.states.get(sensor)
                level = float(state_obj.state) if state_obj else 0.0
            except (ValueError, AttributeError):
                level = 0.0

            if level >= high:
                await self._async_notify(
                    message=f"Wasserstand erholt ({level:.0f}%). Weiter mit nächstem Block."
                )
                break

            if (datetime.now() - start).total_seconds() >= timeout_s:
                await self._async_notify(
                    message="Timeout: Wasserstand nicht erholt. Bewässerung abgebrochen."
                )
                await self.async_stop_watering()
                return

            await asyncio.sleep(30)

    async def _async_trigger_next_zone(self) -> None:
        next_coord = self._get_next_zone_coordinator()
        if next_coord and next_coord._state == STATE_IDLE:
            instance = self.options.get(CONF_INSTANCE_NAME, "")
            await self._async_notify(
                message=f"Zone '{instance}' fertig. Starte nächste Zone."
            )
            await next_coord.async_start_watering(force=True)

    # --- Wind ---

    async def _async_check_wind(self, _event) -> None:
        opts = self.options
        speed_sensor = opts.get(CONF_WIND_SPEED_SENSOR)
        gust_sensor = opts.get(CONF_WIND_GUST_SENSOR)
        speed_limit = opts.get(CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT)
        gust_limit = opts.get(CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT)

        try:
            speed = float(self.hass.states.get(speed_sensor).state)
            gust = float(self.hass.states.get(gust_sensor).state)
        except (ValueError, AttributeError):
            return

        if self._state == STATE_WATERING and (speed > speed_limit or gust > gust_limit):
            self._state = STATE_WIND_HOLD
            await self._async_pump_off()
            await self._async_notify(
                message=f"Wind-Pause: {speed:.1f} km/h / Böe {gust:.1f} km/h"
            )
            self.async_update_listeners()

        elif self._state == STATE_WIND_HOLD and speed <= speed_limit and gust <= gust_limit:
            self._state = STATE_WATERING
            await self._async_pump_on()
            await self._async_notify(message="Wind nachgelassen. Bewässerung fortgesetzt.")
            self.async_update_listeners()

    async def _async_water_level_changed(self, _event) -> None:
        if self._state != STATE_WATERING:
            return
        opts = self.options
        sensor = opts.get(CONF_WATER_LEVEL_SENSOR)
        low = opts.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)
        try:
            level = float(self.hass.states.get(sensor).state)
        except (ValueError, AttributeError):
            return
        if level < low and self._watering_task and not self._watering_task.done():
            # Block unterbrechen – Pause-Sensor-Logik greift im Cycle
            pass

    # --- Background Check ---

    async def _async_background_check(self, _now) -> None:
        if self._should_start_auto():
            await self.async_start_watering()

    # --- Pump helpers ---

    async def _async_pump_on(self) -> None:
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": pump}, blocking=True
            )

    async def _async_pump_off(self) -> None:
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": pump}, blocking=True
            )

    # --- Notify ---

    async def _async_notify(self, message: str, title: str | None = None) -> None:
        if title is None:
            instance = self.options.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung")
            title = f"Brunnen Bewässerung – {instance}"

        try:
            if self.hass.services.has_service("script", "master_notify_v1_1_0"):
                await self.hass.services.async_call(
                    "script",
                    "master_notify_v1_1_0",
                    {
                        "title": title,
                        "message": message,
                        "group_admins_enable": True,
                        "group_family_enable": True,
                        "alexa_enabled": False,
                        "google_enabled": False,
                        "critical_enabled": False,
                    },
                    blocking=False,
                )
                return
        except Exception:
            pass

        self.hass.components.persistent_notification.async_create(
            message, title=title
        )

    # --- Calculations ---

    def _calculate_runtime(self) -> float:
        opts = self.options
        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        target = float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))
        sek_pro_prozent = float(opts.get(CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT))
        min_s = float(opts.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME)) * 60
        max_s = float(opts.get(CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME)) * 60

        try:
            current = float(self.hass.states.get(moisture_sensor).state)
        except (ValueError, AttributeError):
            return 0.0

        if current >= target:
            return 0.0

        duration_s = (target - current) * sek_pro_prozent
        return max(min_s, min(duration_s, max_s))

    def _should_start_auto(self) -> bool:
        if self._state != STATE_IDLE:
            return False
        if not self._auto_mode:
            return False
        if not self._enabled:
            return False
        if self._last_run == date.today():
            return False

        opts = self.options
        earliest_str = opts.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)
        try:
            parts = earliest_str.split(":")
            h, m = int(parts[0]), int(parts[1])
            earliest = time(h, m)
        except (ValueError, AttributeError):
            return False

        current_time = now().time()
        if current_time < earliest:
            return False

        solar_sensor = opts.get(CONF_SOLAR_SENSOR)
        solar_threshold = float(opts.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD))
        try:
            solar = float(self.hass.states.get(solar_sensor).state)
            if solar >= solar_threshold:
                return False
        except (ValueError, AttributeError):
            return False

        giess_enabled = opts.get(CONF_GIESS_ENABLED, True)
        if giess_enabled:
            giess_sensor = opts.get(CONF_GIESS_SENSOR)
            if giess_sensor:
                state_obj = self.hass.states.get(giess_sensor)
                if state_obj and state_obj.state != "on":
                    return False

        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        try:
            current = float(self.hass.states.get(moisture_sensor).state)
            target = float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))
            if current >= target:
                return False
        except (ValueError, AttributeError):
            return False

        return True

    def _get_next_start_info(self) -> str:
        if self._state == STATE_WATERING:
            return "Läuft"
        if self._state == STATE_PAUSING:
            return f"Pause ({self._remaining_s / 60:.0f} Min Rest)"
        if self._state == STATE_WAITING_WATER:
            return "Wartet auf Brunnen"
        if self._state == STATE_WIND_HOLD:
            return "Wind-Pause"
        if not self._enabled:
            return "Deaktiviert"
        if not self._auto_mode:
            return "Manuell"
        if self._last_run == date.today():
            return "Heute schon gelaufen"

        opts = self.options
        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        target = float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))
        try:
            current = float(self.hass.states.get(moisture_sensor).state)
            if current >= target:
                return "Boden feucht genug"
        except (ValueError, AttributeError):
            pass

        giess_enabled = opts.get(CONF_GIESS_ENABLED, True)
        if giess_enabled:
            giess_sensor = opts.get(CONF_GIESS_SENSOR)
            if giess_sensor:
                state_obj = self.hass.states.get(giess_sensor)
                if state_obj and state_obj.state != "on":
                    return "Heute nicht nötig"

        earliest_str = opts.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START)
        try:
            parts = earliest_str.split(":")
            h, m = int(parts[0]), int(parts[1])
            earliest = time(h, m)
        except (ValueError, AttributeError):
            return "Unbekannt"

        current_time = now().time()
        solar_sensor = opts.get(CONF_SOLAR_SENSOR)
        solar_threshold = float(opts.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD))
        try:
            solar = float(self.hass.states.get(solar_sensor).state)
            solar_ok = solar < solar_threshold
        except (ValueError, AttributeError):
            solar_ok = False

        if current_time >= earliest and solar_ok:
            return "Jetzt"
        if current_time >= earliest:
            return "Wartet auf Sonne"
        return f"{earliest_str} Uhr"

    def _has_water_level_sensor(self) -> bool:
        val = self.options.get(CONF_WATER_LEVEL_SENSOR)
        return bool(val)

    def _get_next_zone_coordinator(self) -> "BrunnenBewasserungCoordinator | None":
        next_id = self.options.get(CONF_NEXT_ZONE_ENTRY_ID)
        if not next_id:
            return None
        return self.hass.data.get(DOMAIN, {}).get(next_id)
