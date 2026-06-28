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
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    CONF_PUMP_SWITCH,
    MODE_AUTO, MODE_CHAIN, MODE_MANUAL, CONF_MODE, DEFAULT_MODE,
    CONF_CHAIN_POSITION, DEFAULT_CHAIN_POSITION,
    CONF_MANUAL_DURATION, DEFAULT_MANUAL_DURATION,
    CONF_NOTIFY_SERVICE,
    CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK,
    CONF_NOTIFY_ON_START, CONF_NOTIFY_ON_FINISH, CONF_NOTIFY_ON_BLOCK_PAUSE,
    CONF_NOTIFY_ON_STOP, CONF_NOTIFY_ON_WIND, CONF_NOTIFY_ON_WATER_LEVEL,
    CONF_NOTIFY_ON_NEXT_ZONE, CONF_NOTIFY_ON_NO_WATER_NEEDED,
    DEFAULT_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_BLOCK_PAUSE,
    DEFAULT_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WATER_LEVEL,
    DEFAULT_NOTIFY_ON_NEXT_ZONE, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED,
    CONF_NOTIFY_TITLE,
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
        self._block_start_time: float = 0.0
        self._current_block_s: float = 0.0
        self._tick_task: asyncio.Task | None = None
        self._block_start_time: float = 0.0
        self._current_block_s: float = 0.0
        self._tick_task: asyncio.Task | None = None
        self._remaining_s: float = 0.0
        self._block_remaining_s: float = 0.0
        self._current_block: int = 0
        self._total_blocks: int = 0
        self._last_run: date | None = None
        self._mode: str = MODE_AUTO  # MODE_AUTO | MODE_CHAIN | MODE_MANUAL
        self._enabled: bool = True  # Aktivierungs-Schalter: darf Automatik starten?
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
    def block_remaining_s(self) -> float:
        """Verbleibende Sekunden im aktuellen Block - live berechnet."""
        if self._state == STATE_WATERING and self._block_start_time > 0:
            elapsed = asyncio.get_event_loop().time() - self._block_start_time
            remaining = self._current_block_s - elapsed
            return max(0.0, remaining)
        return 0.0

    @property
    def block_remaining_s(self) -> float:
        """Verbleibende Sekunden im aktuellen Block - live berechnet."""
        if self._state == STATE_WATERING and self._block_start_time > 0:
            elapsed = asyncio.get_event_loop().time() - self._block_start_time
            remaining = self._current_block_s - elapsed
            return max(0.0, remaining)
        return 0.0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def auto_mode(self) -> bool:
        return self._mode == MODE_AUTO

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_active(self) -> bool:
        return self._mode != MODE_MANUAL or self._state == STATE_WATERING

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
        # Pumpe sicherheitshalber ausschalten beim Start
        await self._async_pump_off()
        self._state = STATE_IDLE
        self._remaining_s = 0.0
        self._block_remaining_s = 0.0
        self._current_block = 0
        # Modus aus gespeicherter Config laden
        self._mode = self.options.get(CONF_MODE, DEFAULT_MODE)
        # _last_run aus persistentem Storage laden (im Executor - nicht blockierend)
        try:
            last_run_str, enabled = await self.hass.async_add_executor_job(self._load_state_sync)
            self._enabled = enabled
            if last_run_str:
                self._last_run = date.fromisoformat(last_run_str)
        except Exception:
            self._last_run = None

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

        # Frühestzeit-Trigger: genau zur konfigurierten Startzeit checken
        self._solar_unsub = None
        try:
            parts = opts.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START).split(":")
            h, m = int(parts[0]), int(parts[1])
            self._earliest_unsub = async_track_time_change(
                self.hass, self._async_background_check, hour=h, minute=m, second=0
            )
        except Exception:
            self._earliest_unsub = None

        water_sensor = opts.get(CONF_WATER_LEVEL_SENSOR)
        if water_sensor:
            self._water_level_unsub = async_track_state_change_event(
                self.hass, [water_sensor], self._async_water_level_changed
            )

        return True

    async def async_shutdown(self) -> None:
        for unsub in (self._wind_unsub, self._time_unsub, self._water_level_unsub,
                      getattr(self, '_solar_unsub', None), getattr(self, '_earliest_unsub', None)):
            if unsub:
                unsub()
        self._wind_unsub = None
        self._time_unsub = None
        self._water_level_unsub = None
        self._solar_unsub = None
        self._earliest_unsub = None
        await self.async_stop_watering()

    # --- Public API ---

    async def async_start_watering(self, force: bool = False) -> bool:
        if self._state != STATE_IDLE:
            return False
        if self._mode == MODE_CHAIN and not force:
            return False  # Kette startet nur via force (getriggert von anderer Zone)

        if self._mode == MODE_MANUAL:
            # Manuell: immer feste konfigurierte Laufzeit
            opts = self.options
            runtime_s = float(opts.get(CONF_MANUAL_DURATION, DEFAULT_MANUAL_DURATION)) * 60
        else:
            runtime_s = self._calculate_runtime()
            if runtime_s <= 0:
                if force:
                    opts = self.options
                    runtime_s = float(opts.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME)) * 60
                else:
                    if self._should_notify(CONF_NOTIFY_ON_NO_WATER_NEEDED, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED):
                        await self._async_notify(message="Bodenfeuchte bereits ausreichend – keine Bewässerung nötig.")
                    return False

        if not force and self._last_run == now().date():
            return False

        self._pause_mode = "sensor" if self._has_water_level_sensor() else "time"
        opts = self.options
        block_s = min(runtime_s, opts.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION) * 60)
        self._total_blocks = ceil(runtime_s / block_s)
        self._current_block = 1
        self._remaining_s = runtime_s - block_s
        self._watering_task = self.hass.async_create_task(
            self._async_run_watering_cycle(block_s)
        )
        if self._should_notify(CONF_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_START):
            runtime_min = round(runtime_s / 60, 1)
            await self._async_notify(
                message=f"Bewässerung gestartet. Laufzeit: {runtime_min} Min in {self._total_blocks} Block(s)."
            )
        return True

    async def async_stop_watering(self) -> None:
        was_active = self._state != STATE_IDLE
        if self._tick_task:
            self._tick_task.cancel()
            self._tick_task = None
        if self._watering_task:
            self._watering_task.cancel()
            self._watering_task = None
        await self._async_pump_off()
        self._state = STATE_IDLE
        if was_active and self._should_notify(CONF_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_STOP):
            await self._async_notify(message="Bewässerung manuell abgebrochen.")
        self._remaining_s = 0.0
        self._block_remaining_s = 0.0
        self._current_block = 0
        self.async_update_listeners()

    async def async_skip_today(self) -> None:
        self._last_run = now().date()
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
                    # Erst jetzt als "heute gegossen" markieren
                    self._last_run = now().date()
                    await self._async_save_last_run(self._last_run.isoformat())
                    self.async_update_listeners()
                    if self._should_notify(CONF_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_FINISH):
                        await self._async_notify(message="Bewässerung vollständig abgeschlossen.")
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

                # Restzeit zu klein für eigenen Block?
                # Auf aktuellen Block draufrechnen statt Mini-Block
                opts = self.options
                MIN_BLOCK_S = float(opts.get(CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK)) * 60
                if 0 < self._remaining_s < MIN_BLOCK_S:
                    next_block_s += self._remaining_s
                    self._remaining_s = 0.0

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
            self.async_update_listeners()

    async def _async_run_pause_time(self) -> None:
        opts = self.options
        pause_s = opts.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION) * 60
        self._state = STATE_PAUSING
        self._block_remaining_s = pause_s
        self.async_update_listeners()
        if self._should_notify(CONF_NOTIFY_ON_BLOCK_PAUSE, DEFAULT_NOTIFY_ON_BLOCK_PAUSE):
            await self._async_notify(
                message=f"Block {self._current_block}/{self._total_blocks} beendet. "
                        f"Pause {int(pause_s // 60)} Min. Restzeit: {self._remaining_s / 60:.0f} Min."
            )
        step = 1.0
        elapsed = 0.0
        while elapsed < pause_s:
            await asyncio.sleep(step)
            elapsed += step
            self._block_remaining_s = max(0.0, pause_s - elapsed)
            self.async_update_listeners()

    async def _async_run_pause_sensor(self) -> None:
        opts = self.options
        low = opts.get(CONF_WATER_LEVEL_LOW, DEFAULT_WATER_LEVEL_LOW)
        high = opts.get(CONF_WATER_LEVEL_HIGH, DEFAULT_WATER_LEVEL_HIGH)
        timeout_s = opts.get(CONF_WATER_LEVEL_TIMEOUT, DEFAULT_WATER_LEVEL_TIMEOUT) * 60
        sensor = opts.get(CONF_WATER_LEVEL_SENSOR)

        self._state = STATE_WAITING_WATER
        self.async_update_listeners()
        if self._should_notify(CONF_NOTIFY_ON_WATER_LEVEL, DEFAULT_NOTIFY_ON_WATER_LEVEL):
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
                if self._should_notify(CONF_NOTIFY_ON_WATER_LEVEL, DEFAULT_NOTIFY_ON_WATER_LEVEL):
                    await self._async_notify(
                        message=f"Wasserstand erholt ({level:.0f}%). Weiter mit nächstem Block."
                    )
                break

            if (datetime.now() - start).total_seconds() >= timeout_s:
                if self._should_notify(CONF_NOTIFY_ON_WATER_LEVEL, DEFAULT_NOTIFY_ON_WATER_LEVEL):
                    await self._async_notify(
                        message="Timeout: Wasserstand nicht erholt. Bewässerung abgebrochen."
                    )
                await self.async_stop_watering()
                return

            await asyncio.sleep(30)

    async def _async_trigger_next_zone(self) -> None:
        """Startet die nächste Ketten-Zone nach Position sortiert."""
        from .const import DOMAIN
        all_coordinators = [
            coord for coord in self.hass.data.get(DOMAIN, {}).values()
            if hasattr(coord, '_mode') and coord._mode == MODE_CHAIN
            and coord._state == STATE_IDLE
            and getattr(coord, '_enabled', True)
            and coord is not self
        ]
        if not all_coordinators:
            return
        # Nach Kettenposition sortieren
        all_coordinators.sort(
            key=lambda c: int(c.options.get(CONF_CHAIN_POSITION, DEFAULT_CHAIN_POSITION))
        )
        next_coord = all_coordinators[0]
        instance = self.options.get(CONF_INSTANCE_NAME, "")
        next_instance = next_coord.options.get(CONF_INSTANCE_NAME, "")
        if self._should_notify(CONF_NOTIFY_ON_NEXT_ZONE, DEFAULT_NOTIFY_ON_NEXT_ZONE):
            await self._async_notify(
                message=f"Zone '{instance}' fertig. Starte '{next_instance}'."
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
            if self._should_notify(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND):
                await self._async_notify(
                    message=f"Wind-Pause: {speed:.1f} km/h / Böe {gust:.1f} km/h"
                )
            self.async_update_listeners()

        elif self._state == STATE_WIND_HOLD and speed <= speed_limit and gust <= gust_limit:
            self._state = STATE_WATERING
            await self._async_pump_on()
            if self._should_notify(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND):
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

    async def _async_save_last_run(self, iso_date: str) -> None:
        """Speichert _last_run persistent als JSON."""
        await self.hass.async_add_executor_job(self._save_last_run_sync, iso_date)

    def _load_state_sync(self) -> tuple[str | None, bool]:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                return data.get("last_run"), data.get("enabled", True)
            except Exception:
                pass
        return None, True

    def _save_last_run_sync(self, iso_date: str) -> None:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        existing = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["last_run"] = iso_date
        with open(path, "w") as f:
            json.dump(existing, f)

    async def async_reset_last_run(self) -> None:
        """Setzt _last_run zurück (für Reset-Button)."""
        self._last_run = None
        await self.hass.async_add_executor_job(self._reset_last_run_sync)
        self.async_update_listeners()

    def _reset_last_run_sync(self) -> None:
        import os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        if os.path.exists(path):
            os.remove(path)

    async def async_set_enabled(self, enabled: bool) -> None:
        """Setzt den Aktivierungs-Schalter und speichert ihn persistent."""
        self._enabled = enabled
        await self.hass.async_add_executor_job(self._save_enabled_sync, enabled)
        self.async_update_listeners()

    def _save_enabled_sync(self, enabled: bool) -> None:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        existing = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["enabled"] = enabled
        with open(path, "w") as f:
            json.dump(existing, f)

    async def _async_pump_on(self) -> None:
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            domain = pump.split(".")[0]
            await self.hass.services.async_call(
                domain, "turn_on", {"entity_id": pump}, blocking=True
            )

    async def _async_pump_off(self) -> None:
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            domain = pump.split(".")[0]
            await self.hass.services.async_call(
                domain, "turn_off", {"entity_id": pump}, blocking=True
            )

    # --- Notify ---

    def _should_notify(self, flag_key: str, default: bool = True) -> bool:
        return bool(self.options.get(flag_key, default))

    async def _async_notify(self, title: str = None, message: str = "") -> None:
        opts = self.options
        instance_name = opts.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung")
        if title is None:
            title = opts.get(CONF_NOTIFY_TITLE) or instance_name

        notify_service = opts.get(CONF_NOTIFY_SERVICE, "")
        if not notify_service:
            # Kein Service konfiguriert → persistent notification als Fallback
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification", "create",
                    {"title": title, "message": message, "notification_id": "brunnen_bewasserung"},
                )
            )
            return

        try:
            parts = notify_service.split(".")
            domain = parts[0]
            service_name = ".".join(parts[1:]) if len(parts) > 1 else ""

            if domain == "script":
                # Script-Domain: master_notify braucht Extra-Felder
                data = {
                    "title": title,
                    "message": message,
                    "group_admins_enable": True,
                    "group_family_enable": True,
                    "alexa_enabled": False,
                    "google_enabled": False,
                    "critical_enabled": False,
                }
                await self.hass.services.async_call(
                    domain, service_name, data, blocking=False,
                )
            elif domain == "notify":
                # Seit HA 2024.x: notify-Entities nutzen notify.send_message mit entity_id
                await self.hass.services.async_call(
                    "notify", "send_message",
                    {"entity_id": notify_service, "message": message, "title": title},
                    blocking=False,
                )
            else:
                # Andere Domains direkt aufrufen
                await self.hass.services.async_call(
                    domain, service_name,
                    {"title": title, "message": message},
                    blocking=False,
                )
        except Exception as e:
            _LOGGER.error("Brunnen Bewässerung Notify Fehler: %s", e)
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification", "create",
                    {"title": title, "message": message, "notification_id": "brunnen_bewasserung"},
                )
            )
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
        if not self._enabled:
            return False
        if self._mode != MODE_AUTO:
            return False
        if self._last_run == now().date():
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
        if not self.auto_mode:
            return "Manuell"
        if self._last_run == now().date():
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
