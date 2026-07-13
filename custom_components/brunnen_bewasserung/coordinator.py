from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now

from .const import (
    DOMAIN,
    ENTRY_TYPE_GARTEN, ENTRY_TYPE_ZONE, CONF_ENTRY_TYPE,
    CONF_GARTEN_NAME, CONF_PARENT_ENTRY_ID,
    CONF_INSTANCE_NAME, CONF_PUMP_SWITCH,
    CONF_MAIN_PUMP_SWITCH, CONF_FLOW_SENSOR,
    CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS,
    CONF_FLOW_IDLE_TIMEOUT, DEFAULT_FLOW_IDLE_TIMEOUT,
    CONF_AUTO_PUMP_OFF, DEFAULT_AUTO_PUMP_OFF,
    CONF_SOLAR_SENSOR, CONF_WIND_SPEED_SENSOR, CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_LIMIT, CONF_WIND_GUST_LIMIT,
    DEFAULT_WIND_SPEED_LIMIT, DEFAULT_WIND_GUST_LIMIT,
    CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD,
    CONF_EARLIEST_START, DEFAULT_EARLIEST_START,
    CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION,
    CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION,
    CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME,
    CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME,
    CONF_GIESS_ENABLED, CONF_GIESS_SENSOR,
    CONF_MOISTURE_SENSOR, CONF_TARGET_MOISTURE, CONF_SECONDS_PER_PERCENT,
    CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME,
    CONF_AUTO_ENABLED, DEFAULT_AUTO_ENABLED,
    CONF_ZONE_START_TIME, DEFAULT_ZONE_START_TIME,
    CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK,
    CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND,
    CONF_NOTIFY_SERVICE, CONF_NOTIFY_TITLE,
    CONF_NOTIFY_ON_START, CONF_NOTIFY_ON_FINISH, CONF_NOTIFY_ON_BLOCK_PAUSE,
    CONF_NOTIFY_ON_STOP, CONF_NOTIFY_ON_WIND, CONF_NOTIFY_ON_NO_WATER_NEEDED,
    DEFAULT_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_BLOCK_PAUSE,
    DEFAULT_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED,
    DEFAULT_TARGET_MOISTURE, DEFAULT_SECONDS_PER_PERCENT,
    STATE_IDLE, STATE_WATERING, STATE_PAUSING, STATE_WIND_HOLD,
    STATE_WAITING_WATER, STATE_WAITING_ZONE,
    STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE,
    ENTRY_TYPE_MANUELL,
)

_LOGGER = logging.getLogger(__name__)
_CHECK_INTERVAL = timedelta(minutes=1)


class GartenCoordinator(DataUpdateCoordinator):
    """Hub: Wetterstation, Pumpe, globaler Durchflusszähler."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_garten")
        self._config_entry = config_entry
        self._flow_counter: float = 0.0          # kumulierter Durchfluss seit letztem Reset
        self._flow_last_value: float = 0.0       # letzter Sensorwert
        self._flow_idle_task: asyncio.Task | None = None
        self._flow_unsub: Callable | None = None

    @property
    def options(self) -> dict:
        merged = dict(self._config_entry.data)
        merged.update(self._config_entry.options)
        return merged

    @property
    def garten_name(self) -> str:
        return self.options.get(CONF_GARTEN_NAME, "Garten")

    @property
    def flow_counter(self) -> float:
        return self._flow_counter

    async def async_setup(self) -> bool:
        # Erst nach vollständigem HA-Start das Tracking einrichten
        async def _start_tracking(_event=None):
            await self._async_update_flow_tracking()

        if self.hass.is_running:
            # HA läuft bereits (z.B. Reload) → sofort starten
            self.hass.async_create_task(_start_tracking())
        else:
            # Beim ersten Start: warten bis HA vollständig hochgefahren ist
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _start_tracking
            )

        # Alle 60s neu prüfen falls neue Zonen hinzukommen
        self._tracking_unsub = async_track_time_interval(
            self.hass, self._async_refresh_tracking, timedelta(minutes=1)
        )
        return True

    async def _async_refresh_tracking(self, _now=None) -> None:
        await self._async_update_flow_tracking()

    async def _async_update_flow_tracking(self) -> None:
        """Überwacht alle Zonen-Durchflusssensoren."""
        old_sensors = set()
        if self._flow_unsub:
            # Merken welche Sensoren bereits getrackt werden
            old_sensors = set(self._get_all_zone_flow_sensors())
            self._flow_unsub()
            self._flow_unsub = None

        sensors = self._get_all_zone_flow_sensors()
        if sensors:
            new_sensors = set(sensors)
            # Nur bei neuen Sensoren den last_value aktualisieren
            if new_sensors != old_sensors:
                # Neue Sensoren → last_value neu setzen
                self._flow_last_value = self._read_total_flow()
                if not old_sensors:
                    # Erster Start → Zähler auf 0
                    self._flow_counter = 0.0
            self._flow_unsub = async_track_state_change_event(
                self.hass, sensors, self._async_flow_changed
            )

    async def async_shutdown(self) -> None:
        if hasattr(self, '_tracking_unsub') and self._tracking_unsub:
            self._tracking_unsub()
            self._tracking_unsub = None
        if self._flow_unsub:
            self._flow_unsub()
            self._flow_unsub = None
        if self._flow_idle_task:
            self._flow_idle_task.cancel()
            self._flow_idle_task = None

    # --- Durchfluss-Logik ---

    async def _async_flow_changed(self, event) -> None:
        # unavailable/unknown ignorieren
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unavailable", "unknown", ""):
            return

        new_val = self._read_total_flow()
        if new_val <= 0:
            return  # Noch nicht bereit

        if self._flow_last_value <= 0:
            # Erster gültiger Wert nach Start/Neustart → nur Ausgangspunkt setzen
            self._flow_last_value = new_val
            self.async_update_listeners()
            return

        if new_val > self._flow_last_value:
            # Durchfluss hat sich erhöht → Differenz aufaddieren
            diff = new_val - self._flow_last_value
            self._flow_counter += diff
            self._flow_last_value = new_val
            # Idle-Timer abbrechen und neu starten
            if self._flow_idle_task and not self._flow_idle_task.done():
                self._flow_idle_task.cancel()
                self._flow_idle_task = None
            self._flow_idle_task = self.hass.async_create_task(
                self._async_flow_idle_countdown()
            )
        elif new_val < self._flow_last_value:
            # Sensor-Wert gesunken (Geräte-Neustart) → nur Ausgangspunkt updaten
            self._flow_last_value = new_val
        # Gleicher Wert: nichts tun

        self.async_update_listeners()

    def _any_zone_active(self, exclude: object | None = None) -> bool:
        """True wenn mindestens eine Zone dieses Gartens gerade aktiv ist
        (inkl. Block-/Wind-/Brunnenpausen - deckt sich mit der Definition
        von binary_sensor.*_bewasserung_aktiv). `exclude` blendet den
        Aufrufer selbst aus, dessen intern gespeicherter State im Moment
        des Aufrufs evtl. noch nicht auf "geschlossen" aktualisiert ist."""
        active_states = {STATE_WATERING, STATE_PAUSING, STATE_WAITING_WATER, STATE_WIND_HOLD, STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE}
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if coord is exclude:
                continue
            # Prüfe ob es ein Zonen-Coordinator ist (hat CONF_PARENT_ENTRY_ID)
            if not hasattr(coord, '_state'):
                continue
            if not hasattr(coord, 'options'):
                continue
            if coord.options.get(CONF_PARENT_ENTRY_ID) != self._config_entry.entry_id:
                continue
            if coord._state in active_states:
                return True
        return False

    def get_open_zones(self) -> list:
        """Alle aktuell offenen Zonen dieses Gartens (Automatik + Manuell)."""
        open_states = {STATE_WATERING, STATE_MANUELL_OPEN}
        result = []
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if not hasattr(coord, "_state") or not hasattr(coord, "options"):
                continue
            if coord.options.get(CONF_PARENT_ENTRY_ID) != self._config_entry.entry_id:
                continue
            if coord._state in open_states:
                result.append(coord)
        return result

    def _any_zone_in_pause(self) -> bool:
        """True wenn irgendeine Zone dieses Gartens gerade Brunnenpause hat."""
        pause_states = {STATE_WAITING_WATER, STATE_MANUELL_PAUSE}
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if not hasattr(coord, "_state") or not hasattr(coord, "options"):
                continue
            if coord.options.get(CONF_PARENT_ENTRY_ID) != self._config_entry.entry_id:
                continue
            if coord._state in pause_states:
                return True
        return False

    def get_pause_remaining_s(self) -> float:
        """Restzeit (Sekunden) der laengsten aktuell laufenden Brunnenpause
        dieses Gartens, 0 wenn keine Zone gerade pausiert."""
        pause_states = {STATE_WAITING_WATER, STATE_MANUELL_PAUSE}
        remaining = 0.0
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if not hasattr(coord, "_state") or not hasattr(coord, "options"):
                continue
            if coord.options.get(CONF_PARENT_ENTRY_ID) != self._config_entry.entry_id:
                continue
            if coord._state in pause_states:
                remaining = max(remaining, getattr(coord, "_block_remaining_s", 0.0) or 0.0)
        return remaining

    def get_automatik_aktiv(self) -> bool:
        """True wenn eine Automatik-Zone dieses Gartens gerade bewaessert
        oder auf ihren Start wartet (z.B. weil eine Brunnenpause laeuft)."""
        active_states = {STATE_WATERING, STATE_WAITING_ZONE}
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if not hasattr(coord, "_state") or not hasattr(coord, "options"):
                continue
            if coord.options.get(CONF_PARENT_ENTRY_ID) != self._config_entry.entry_id:
                continue
            if coord._state in active_states:
                return True
        return False

    async def _async_flow_idle_countdown(self) -> None:
        """Wartet X Minuten ohne Durchfluss-Änderung dann Reset."""
        try:
            timeout_min = float(self.options.get(CONF_FLOW_IDLE_TIMEOUT, DEFAULT_FLOW_IDLE_TIMEOUT))
            await asyncio.sleep(timeout_min * 60)
            _LOGGER.debug("Brunnen: Kein Durchfluss für %.0f Min. → Zähler reset.", timeout_min)
            self._flow_counter = 0.0
            self._flow_last_value = self._read_total_flow()
            self.async_update_listeners()
        except asyncio.CancelledError:
            pass  # Timer wurde abgebrochen weil neuer Durchfluss kam

    def _get_all_zone_flow_sensors(self) -> list[str]:
        """Gibt alle konfigurierten Zonen-Durchflusssensoren zurück (Automatik + Manuell)."""
        sensors = []
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if isinstance(coord, (BrunnenBewasserungCoordinator, ManuelleZoneCoordinator)):
                parent = coord.options.get(CONF_PARENT_ENTRY_ID)
                if parent == self._config_entry.entry_id:
                    sensor = coord.options.get(CONF_FLOW_SENSOR)
                    if sensor:
                        sensors.append(sensor)
        return sensors

    def _read_total_flow(self) -> float:
        """Summiert den aktuellen Durchfluss aller Zonen (Automatik + Manuell)."""
        total = 0.0
        for coord in self.hass.data.get(DOMAIN, {}).values():
            if isinstance(coord, (BrunnenBewasserungCoordinator, ManuelleZoneCoordinator)):
                parent = coord.options.get(CONF_PARENT_ENTRY_ID)
                if parent == self._config_entry.entry_id:
                    sensor = coord.options.get(CONF_FLOW_SENSOR)
                    if sensor:
                        try:
                            total += float(self.hass.states.get(sensor).state)
                        except (ValueError, AttributeError):
                            pass
        return total

    def get_flow_since(self, start_value: float) -> float:
        """Liter seit einem bestimmten Startwert des Zählers."""
        return max(0.0, self._flow_counter - start_value)

    def has_flow_sensor(self) -> bool:
        """True wenn mindestens eine Zone einen Durchflusssensor hat."""
        return len(self._get_all_zone_flow_sensors()) > 0

    def get_flow_pause_liters(self) -> float:
        return float(self.options.get(CONF_FLOW_PAUSE_LITERS, DEFAULT_FLOW_PAUSE_LITERS))

    # --- Wetter ---

    def get_wind_ok(self) -> bool:
        opts = self.options
        try:
            speed = float(self.hass.states.get(opts.get(CONF_WIND_SPEED_SENSOR)).state)
            gust = float(self.hass.states.get(opts.get(CONF_WIND_GUST_SENSOR)).state)
            return (speed <= float(opts.get(CONF_WIND_SPEED_LIMIT, DEFAULT_WIND_SPEED_LIMIT)) and
                    gust <= float(opts.get(CONF_WIND_GUST_LIMIT, DEFAULT_WIND_GUST_LIMIT)))
        except (ValueError, AttributeError):
            return True

    def get_solar_ok(self) -> bool:
        try:
            solar = float(self.hass.states.get(self.options.get(CONF_SOLAR_SENSOR)).state)
            return solar < float(self.options.get(CONF_SOLAR_THRESHOLD, DEFAULT_SOLAR_THRESHOLD))
        except (ValueError, AttributeError):
            return False

    def get_earliest_start(self) -> time | None:
        try:
            parts = self.options.get(CONF_EARLIEST_START, DEFAULT_EARLIEST_START).split(":")
            return time(int(parts[0]), int(parts[1]))
        except Exception:
            return None

    def get_giess_ok(self) -> bool:
        opts = self.options
        if not opts.get(CONF_GIESS_ENABLED, True):
            return True
        sensor = opts.get(CONF_GIESS_SENSOR)
        if not sensor:
            return True
        state_obj = self.hass.states.get(sensor)
        if not state_obj:
            return True
        return state_obj.state in ("on", "true", "True", "1")

    def get_block_duration(self) -> float:
        return float(self.options.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION))

    def get_pause_duration(self) -> float:
        return float(self.options.get(CONF_PAUSE_DURATION, DEFAULT_PAUSE_DURATION))

    def get_min_runtime(self) -> float:
        return float(self.options.get(CONF_MIN_RUNTIME, DEFAULT_MIN_RUNTIME))

    def get_max_runtime(self) -> float:
        return float(self.options.get(CONF_MAX_RUNTIME, DEFAULT_MAX_RUNTIME))

    # --- Pumpe ---

    async def async_main_pump_on(self) -> None:
        pump = self.options.get(CONF_MAIN_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                pump.split(".")[0], "turn_on", {"entity_id": pump}, blocking=True
            )
            await asyncio.sleep(2)

    async def async_main_pump_off(self, exclude: object | None = None) -> None:
        if not self.options.get(CONF_AUTO_PUMP_OFF, DEFAULT_AUTO_PUMP_OFF):
            return  # Pumpe wird extern gesteuert
        # Nur ausschalten wenn wirklich GAR KEINE Zone dieses Gartens mehr
        # aktiv ist - auch nicht in einer Block-/Wind-/Brunnenpause. Das
        # deckt sich mit binary_sensor.*_bewasserung_aktiv und verhindert
        # haeufiges An/Aus-Takten zwischen Bewaesserungs-Bloecken.
        if self._any_zone_active(exclude=exclude):
            return
        pump = self.options.get(CONF_MAIN_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                pump.split(".")[0], "turn_off", {"entity_id": pump}, blocking=True
            )


class BrunnenBewasserungCoordinator(DataUpdateCoordinator):
    """Zone: Bewässerungslogik für eine einzelne Zone."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self._config_entry = config_entry
        self._state: str = STATE_IDLE
        self._remaining_s: float = 0.0
        self._block_remaining_s: float = 0.0
        self._current_block: int = 0
        self._total_blocks: int = 0
        self._last_run: date | None = None
        self._auto_enabled: bool = True
        self._manual_active: bool = False
        self._flow_value_at_start: float = 0.0
        self._in_brunnen_pause: bool = False
        self._watering_task: asyncio.Task | None = None
        self._wind_unsub: Callable | None = None
        self._time_unsub: Callable | None = None
        self._earliest_unsub: Callable | None = None
        self._setup_done: bool = False

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
    def auto_enabled(self) -> bool:
        return self._auto_enabled

    @property
    def manual_active(self) -> bool:
        return self._manual_active

    @property
    def options(self) -> dict:
        merged = dict(self._config_entry.data)
        merged.update(self._config_entry.options)
        return merged

    def get_garten(self) -> GartenCoordinator | None:
        parent_id = self.options.get(CONF_PARENT_ENTRY_ID)
        if not parent_id:
            return None
        coord = self.hass.data.get(DOMAIN, {}).get(parent_id)
        return coord if isinstance(coord, GartenCoordinator) else None

    def _zone_has_flow_sensor(self) -> bool:
        """Prüft direkt in den Zone-Options ob ein Durchflussmesser konfiguriert ist."""
        return bool(self.options.get(CONF_FLOW_SENSOR))

    def _get_zone_start_time(self):
        """Gibt die konfigurierte Startzeit der Zone zurück."""
        from datetime import time as _time
        val = self.options.get(CONF_ZONE_START_TIME, "")
        if not val:
            return None
        try:
            h, m = map(int, val.split(":"))
            return _time(h, m)
        except Exception:
            return None

    async def _register_start_time_trigger(self) -> None:
        """Öffentliche Methode: Zeit-Trigger neu registrieren (z.B. nach Änderung der Startzeit)."""
        start_time = self._get_zone_start_time()
        if self._earliest_unsub:
            self._earliest_unsub()
            self._earliest_unsub = None
        if start_time:
            self._earliest_unsub = async_track_time_change(
                self.hass, self._async_background_check,
                hour=start_time.hour, minute=start_time.minute, second=0
            )

    # --- Setup ---

    async def async_setup(self) -> bool:
        await self._async_pump_off()
        self._state = STATE_IDLE

        try:
            last_run_str, auto_enabled = await self.hass.async_add_executor_job(self._load_state_sync)
            self._auto_enabled = auto_enabled
            if last_run_str:
                self._last_run = date.fromisoformat(last_run_str)
        except Exception:
            self._last_run = None

        garten = self.get_garten()
        wind_entities = []
        if garten:
            g_opts = garten.options
            if g_opts.get(CONF_WIND_SPEED_SENSOR):
                wind_entities.append(g_opts[CONF_WIND_SPEED_SENSOR])
            if g_opts.get(CONF_WIND_GUST_SENSOR):
                wind_entities.append(g_opts[CONF_WIND_GUST_SENSOR])

        if wind_entities:
            self._wind_unsub = async_track_state_change_event(
                self.hass, wind_entities, self._async_check_wind
            )

        self._time_unsub = async_track_time_interval(
            self.hass, self._async_background_check, _CHECK_INTERVAL
        )

        async def _register_time_trigger(_event=None):
            # Eigene Zonen-Startzeit als Trigger setzen
            start_time = self._get_zone_start_time()
            if start_time:
                if self._earliest_unsub:
                    self._earliest_unsub()
                self._earliest_unsub = async_track_time_change(
                    self.hass, self._async_background_check,
                    hour=start_time.hour, minute=start_time.minute, second=0
                )
            self._setup_done = True

        if self.hass.is_running:
            await _register_time_trigger()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _register_time_trigger
            )

        return True

    async def async_shutdown(self) -> None:
        for unsub in (self._wind_unsub, self._time_unsub, self._earliest_unsub):
            if unsub:
                unsub()
        self._wind_unsub = None
        self._time_unsub = None
        self._earliest_unsub = None
        await self.async_stop_watering()

    # --- Public API ---

    async def async_start_watering(self, force: bool = False) -> bool:
        """Startet Bewässerung. force=True überspringt last_run Check."""
        if self._state not in (STATE_IDLE,):
            return False

        garten = self.get_garten()

        if garten and garten._any_zone_in_pause():
            # Brunnen erholt sich gerade (Automatik- oder Manuell-Zone in
            # Pause) - erst starten wenn die Pause vorbei ist. Gilt auch
            # fuer force=True (Start-Button): der Brunnen braucht die
            # Erholzeit unabhaengig davon, warum die Zone starten will.
            self._state = STATE_WAITING_ZONE
            self.async_update_listeners()
            self._watering_task = self.hass.async_create_task(
                self._async_wait_for_zone_and_start(force=force, pause_only=True)
            )
            return True

        runtime_s = self._calculate_runtime()

        if runtime_s <= 0:
            if force:
                runtime_s = (garten.get_min_runtime() if garten else DEFAULT_MIN_RUNTIME) * 60
            else:
                if self._should_notify(CONF_NOTIFY_ON_NO_WATER_NEEDED, DEFAULT_NOTIFY_ON_NO_WATER_NEEDED):
                    await self._async_notify(message="Bodenfeuchte bereits ausreichend.")
                return False

        if not force and self._last_run == now().date():
            return False

        self._flow_value_at_start = garten.flow_counter if garten else 0.0

        import math
        if self._zone_has_flow_sensor():
            # Mit Durchflussmesser: kein Block-Split, Zone läuft durch
            block_s = runtime_s
            self._total_blocks = 1 if not math.isinf(runtime_s) else 0
        else:
            # Ohne Durchflussmesser: Block-Split für Brunnen-Erholung
            block_s_raw = (garten.get_block_duration() if garten else DEFAULT_BLOCK_DURATION) * 60
            block_s = min(runtime_s, block_s_raw)
            self._total_blocks = ceil(runtime_s / block_s) if not math.isinf(runtime_s) else 0

        self._current_block = 1
        # _remaining_s = Gesamtrestzeit (immer volle Laufzeit, wird im Block heruntergezählt)
        self._remaining_s = runtime_s

        self._watering_task = self.hass.async_create_task(
            self._async_run_watering_cycle(block_s, runtime_s)
        )

        if self._should_notify(CONF_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_START):
            rt = "∞" if math.isinf(runtime_s) else str(round(runtime_s / 60, 1))
            await self._async_notify(
                message=f"Bewässerung gestartet. Laufzeit: {rt} Min in {self._total_blocks or '?'} Block(s)."
            )
        return True

    async def async_stop_watering(self) -> None:
        was_active = self._state not in (STATE_IDLE, STATE_WAITING_ZONE)
        self._state = STATE_IDLE
        self._manual_active = False
        if self._watering_task:
            self._watering_task.cancel()
            try:
                await self._watering_task
            except asyncio.CancelledError:
                pass
            self._watering_task = None
        await self._async_pump_off()
        if was_active and self._should_notify(CONF_NOTIFY_ON_STOP, DEFAULT_NOTIFY_ON_STOP):
            await self._async_notify(message="Bewässerung gestoppt.")
        self._remaining_s = 0.0
        self._block_remaining_s = 0.0
        self._current_block = 0
        self.async_update_listeners()

    async def async_set_auto_enabled(self, enabled: bool) -> None:
        self._auto_enabled = enabled
        await self.hass.async_add_executor_job(self._save_auto_enabled_sync, enabled)
        self.async_update_listeners()

    async def async_pause_for_brunnen(self) -> None:
        """Brunnenpause – Pumpe aus, Zustand merken (nur wenn watering)."""
        if self._state == STATE_WATERING:
            self._in_brunnen_pause = True
            await self._async_pump_off()
            self._state = STATE_WAITING_WATER
            self.async_update_listeners()

    async def async_resume_after_brunnen(self) -> None:
        """Nach Brunnenpause: Pumpe wieder an."""
        self._in_brunnen_pause = False
        if self._state == STATE_WAITING_WATER:
            self._state = STATE_WATERING
            await self._async_pump_on()
            self.async_update_listeners()

    async def async_skip_today(self) -> None:
        self._last_run = now().date()
        await self._async_save_last_run(self._last_run.isoformat())
        self.async_update_listeners()

    async def async_reset_last_run(self) -> None:
        self._last_run = None
        await self.hass.async_add_executor_job(self._reset_last_run_sync)
        self.async_update_listeners()

    # --- Watering Cycle ---

    async def _async_run_watering_cycle(self, first_block_s: float, total_runtime_s: float) -> None:
        import math
        garten = self.get_garten()
        block_duration_s = (garten.get_block_duration() if garten else DEFAULT_BLOCK_DURATION) * 60
        current_block_s = first_block_s
        infinite = math.isinf(total_runtime_s)

        try:
            while True:
                # Wind prüfen bevor Block startet
                garten_check = self.get_garten()
                ignore_wind = self.options.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND)
                if garten_check and not ignore_wind and not garten_check.get_wind_ok():
                    # Wind zu stark → warten bis Wind nachlässt
                    self._state = STATE_WIND_HOLD
                    self.async_update_listeners()
                    if self._should_notify(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND):
                        await self._async_notify(message="Wind zu stark – warte auf Windberuhigung.")
                    while not ignore_wind and garten_check and not garten_check.get_wind_ok():
                        await asyncio.sleep(30)
                        if self._state == STATE_IDLE:
                            return
                    self._state = STATE_WATERING
                    self.async_update_listeners()
                else:
                    self._state = STATE_WATERING
                    self.async_update_listeners()
                await self._async_pump_on()
                await self._async_run_block(current_block_s)
                await self._async_pump_off()

                remaining = self._remaining_s

                # Durchfluss-Check: auch nach Block-Ende prüfen
                # (MQTT-Updates kommen verzögert vom Sonoff)
                if self._zone_has_flow_sensor() and garten:
                    flow_since = garten.get_flow_since(self._flow_value_at_start)
                    if flow_since >= garten.get_flow_pause_liters():
                        await self._async_run_pause_flow(garten)
                        if self._state == STATE_IDLE:
                            break
                        self._flow_value_at_start = garten.flow_counter
                        self._current_block += 1
                        # Nach Pause: Lauf beendet wenn keine Restzeit mehr
                        if not infinite and self._remaining_s <= 0:
                            self._state = STATE_IDLE
                            self._current_block = 0
                            self._last_run = now().date()
                            await self._async_save_last_run(self._last_run.isoformat())
                            self.async_update_listeners()
                            if self._should_notify(CONF_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_FINISH):
                                await self._async_notify(message="Bewässerung abgeschlossen.")
                            break
                        continue

                if not infinite and remaining <= 0:
                    self._state = STATE_IDLE
                    self._current_block = 0
                    self._last_run = now().date()
                    await self._async_save_last_run(self._last_run.isoformat())
                    self.async_update_listeners()
                    if self._should_notify(CONF_NOTIFY_ON_FINISH, DEFAULT_NOTIFY_ON_FINISH):
                        await self._async_notify(message="Bewässerung abgeschlossen.")
                    break

                # Brunnenpause nach Durchfluss-Limit
                if self._zone_has_flow_sensor() and garten:
                    await self._async_run_pause_flow(garten)
                    # Nach Pause: weiter mit Rest-Laufzeit (kein Block-Split)
                    if self._state == STATE_IDLE:
                        break
                    # Startwert aktualisieren für nächsten Durchfluss-Zyklus
                    self._flow_value_at_start = garten.flow_counter
                    self._current_block += 1
                    # Restlaufzeit bleibt unverändert - Block läuft weiter
                else:
                    # Ohne Durchflussmesser: Zeit-basierte Blocks
                    await self._async_run_pause_time(garten)
                    if self._state == STATE_IDLE:
                        break
                    self._current_block += 1
                    if not infinite:
                        min_block_s = float(self.options.get(CONF_MIN_REMAINDER_BLOCK, DEFAULT_MIN_REMAINDER_BLOCK)) * 60
                        next_block_s = min(self._remaining_s, block_duration_s)
                        self._remaining_s -= next_block_s
                        if 0 < self._remaining_s < min_block_s:
                            next_block_s += self._remaining_s
                            self._remaining_s = 0.0
                        current_block_s = next_block_s
                    else:
                        current_block_s = block_duration_s

        except asyncio.CancelledError:
            pass

    async def _async_run_block(self, duration_s: float) -> None:
        import math
        self._block_remaining_s = duration_s
        step = 1.0
        elapsed = 0.0
        infinite = math.isinf(duration_s)
        garten = self.get_garten()
        flow_limit = garten.get_flow_pause_liters() if garten else DEFAULT_FLOW_PAUSE_LITERS

        try:
            while infinite or elapsed < duration_s:
                await asyncio.sleep(step)
                # Wind-Hold: Zeit nicht weiterzählen
                if self._state == STATE_WIND_HOLD:
                    continue
                elapsed += step
                if not infinite:
                    self._block_remaining_s = max(0.0, duration_s - elapsed)
                    self._remaining_s = max(0.0, self._remaining_s - step)
                if self._zone_has_flow_sensor() and garten:
                    if garten.get_flow_since(self._flow_value_at_start) >= flow_limit:
                        self.async_update_listeners()
                        return
                self.async_update_listeners()
        except asyncio.CancelledError:
            raise

    async def _async_run_pause_time(self, garten) -> None:
        pause_s = (garten.get_pause_duration() if garten else DEFAULT_PAUSE_DURATION) * 60
        self._state = STATE_PAUSING
        self._block_remaining_s = pause_s
        self.async_update_listeners()
        if self._should_notify(CONF_NOTIFY_ON_BLOCK_PAUSE, DEFAULT_NOTIFY_ON_BLOCK_PAUSE):
            await self._async_notify(
                message=f"Block {self._current_block}/{self._total_blocks or '?'} fertig. Pause {int(pause_s // 60)} Min."
            )
        step = 1.0
        elapsed = 0.0
        try:
            while elapsed < pause_s:
                await asyncio.sleep(step)
                elapsed += step
                self._block_remaining_s = max(0.0, pause_s - elapsed)
                self.async_update_listeners()
        except asyncio.CancelledError:
            return

    async def _async_run_pause_flow(self, garten: GartenCoordinator) -> None:
        pause_s = garten.get_pause_duration() * 60
        self._state = STATE_WAITING_WATER
        self._block_remaining_s = pause_s
        self.async_update_listeners()
        if self._should_notify(CONF_NOTIFY_ON_BLOCK_PAUSE, DEFAULT_NOTIFY_ON_BLOCK_PAUSE):
            await self._async_notify(
                message=f"Brunnenpause {int(pause_s // 60)} Min. ({garten.get_flow_pause_liters():.0f}L erreicht)."
            )
        step = 1.0
        elapsed = 0.0
        try:
            while elapsed < pause_s:
                if self._state == STATE_IDLE:
                    return
                await asyncio.sleep(step)
                elapsed += step
                self._block_remaining_s = max(0.0, pause_s - elapsed)
                self.async_update_listeners()
        except asyncio.CancelledError:
            return
        self._flow_value_at_start = garten.flow_counter

    # --- Wind ---

    async def _async_check_wind(self, _event) -> None:
        # Windpause für diese Zone ignorieren?
        if self.options.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND):
            return
        garten = self.get_garten()
        if not garten:
            return
        wind_ok = garten.get_wind_ok()
        if self._state == STATE_WATERING and not wind_ok:
            self._state = STATE_WIND_HOLD
            await self._async_pump_off()
            if self._should_notify(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND):
                await self._async_notify(message="Wind-Pause: Zu starker Wind.")
            self.async_update_listeners()
        elif self._state == STATE_WIND_HOLD and wind_ok:
            self._state = STATE_WATERING
            await self._async_pump_on()
            if self._should_notify(CONF_NOTIFY_ON_WIND, DEFAULT_NOTIFY_ON_WIND):
                await self._async_notify(message="Wind nachgelassen. Weiter.")
            self.async_update_listeners()

    # --- Background Check ---

    async def _async_background_check(self, _now) -> None:
        if not self._setup_done:
            return
        self.async_update_listeners()  # Nächster-Start Sensor aktuell halten
        if self._should_start_auto():
            garten = self.get_garten()
            if garten and garten._any_zone_active():
                # Andere Zone aktiv → Warte-Task starten falls noch nicht aktiv
                if self._state == STATE_IDLE:
                    self._state = STATE_WAITING_ZONE
                    self.async_update_listeners()
                    self._watering_task = self.hass.async_create_task(
                        self._async_wait_for_zone_and_start()
                    )
            else:
                await self.async_start_watering()

    def _should_start_auto(self) -> bool:
        if self._state not in (STATE_IDLE,):
            return False
        if not self._auto_enabled:
            return False
        if self._last_run == now().date():
            return False

        garten = self.get_garten()
        if not garten:
            return False

        # Eigene Zonen-Startzeit prüfen
        start_time = self._get_zone_start_time()
        if not start_time or now().time() < start_time:
            return False

        # Globales "nicht vor" Limit des Gartens
        earliest = garten.get_earliest_start()
        if earliest and now().time() < earliest:
            return False

        if not garten.get_solar_ok():
            return False
        if not garten.get_wind_ok() and not self.options.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND):
            return False
        if not garten.get_giess_ok():
            return False

        opts = self.options
        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        if moisture_sensor:
            try:
                current = float(self.hass.states.get(moisture_sensor).state)
                target = float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))
                if current >= target:
                    return False
            except (ValueError, AttributeError):
                return False

        return True

    # --- Pump ---

    async def _async_pump_on(self) -> None:
        garten = self.get_garten()
        if garten:
            await garten.async_main_pump_on()
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                pump.split(".")[0], "turn_on", {"entity_id": pump}, blocking=True
            )

    async def _async_pump_off(self) -> None:
        pump = self.options.get(CONF_PUMP_SWITCH)
        if pump:
            await self.hass.services.async_call(
                pump.split(".")[0], "turn_off", {"entity_id": pump}, blocking=True
            )
        garten = self.get_garten()
        if garten:
            await garten.async_main_pump_off(exclude=self)

    # --- Storage ---

    def _load_state_sync(self) -> tuple[str | None, bool]:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                return data.get("last_run"), data.get("auto_enabled", True)
            except Exception:
                pass
        return None, True

    async def _async_save_last_run(self, iso_date: str) -> None:
        await self.hass.async_add_executor_job(self._save_last_run_sync, iso_date)

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

    def _reset_last_run_sync(self) -> None:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                data.pop("last_run", None)
                with open(path, "w") as f:
                    json.dump(data, f)
            except Exception:
                os.remove(path)

    def _save_auto_enabled_sync(self, enabled: bool) -> None:
        import json, os
        path = self.hass.config.path(".storage", f"brunnen_bewasserung_{self._config_entry.entry_id}.json")
        existing = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["auto_enabled"] = enabled
        with open(path, "w") as f:
            json.dump(existing, f)

    # --- Runtime Calculation ---

    def _calculate_runtime(self) -> float:
        opts = self.options
        garten = self.get_garten()
        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        min_s = (garten.get_min_runtime() if garten else DEFAULT_MIN_RUNTIME) * 60
        max_s = (garten.get_max_runtime() if garten else DEFAULT_MAX_RUNTIME) * 60

        if not moisture_sensor:
            return float(opts.get(CONF_FIXED_RUNTIME, DEFAULT_FIXED_RUNTIME)) * 60

        target = float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE))
        sek_pro_prozent = float(opts.get(CONF_SECONDS_PER_PERCENT, DEFAULT_SECONDS_PER_PERCENT))
        try:
            current = float(self.hass.states.get(moisture_sensor).state)
        except (ValueError, AttributeError):
            return 0.0

        if current >= target:
            return 0.0

        duration_s = (target - current) * sek_pro_prozent
        return max(min_s, min(duration_s, max_s))

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
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification", "create",
                    {"title": title, "message": message, "notification_id": "brunnen_bewasserung"},
                )
            )
            return

        async def _send():
            try:
                parts = notify_service.split(".")
                domain = parts[0]
                service_name = ".".join(parts[1:]) if len(parts) > 1 else ""
                if domain == "script":
                    await self.hass.services.async_call(domain, service_name, {
                        "title": title, "message": message,
                        "group_admins_enable": True, "group_family_enable": True,
                        "alexa_enabled": False, "google_enabled": False, "critical_enabled": False,
                    }, blocking=False)
                elif domain == "notify":
                    await self.hass.services.async_call("notify", "send_message",
                        {"entity_id": notify_service, "message": message, "title": title}, blocking=False)
                else:
                    await self.hass.services.async_call(domain, service_name,
                        {"title": title, "message": message}, blocking=False)
            except Exception as e:
                _LOGGER.error("Brunnen Notify Fehler: %s", e)

        self.hass.async_create_task(_send())

    async def _async_wait_for_zone_and_start(self, force: bool = False, pause_only: bool = False) -> None:
        """Wartet bis die Brunnenpause vorbei ist (pause_only=True) oder bis
        wirklich alle anderen Zonen fertig sind (pause_only=False, fuer die
        klassische Zonen-Wartekette beim geplanten Auto-Start), dann starten."""
        try:
            while self._state == STATE_WAITING_ZONE:
                await asyncio.sleep(30)
                garten = self.get_garten()
                if not garten:
                    break
                still_blocked = garten._any_zone_in_pause() if pause_only else garten._any_zone_active()
                if not still_blocked:
                    self._state = STATE_IDLE
                    if force or self._should_start_auto():
                        await self.async_start_watering(force=force)
                    break
                self.async_update_listeners()
        except asyncio.CancelledError:
            if self._state == STATE_WAITING_ZONE:
                self._state = STATE_IDLE
            self.async_update_listeners()

    def _get_next_start_info(self) -> str:
        if self._state == STATE_WATERING:
            return "Läuft"
        if self._state == STATE_WAITING_ZONE:
            return "Wartet auf andere Zone"
        if self._state in (STATE_PAUSING, STATE_WAITING_WATER):
            return f"Pause ({self._block_remaining_s / 60:.0f} Min)"
        if self._state == STATE_WIND_HOLD:
            return "Wind-Pause"
        if not self._auto_enabled:
            return "Automatik aus"
        if self._last_run == now().date():
            return "Heute schon gelaufen"

        garten = self.get_garten()
        opts = self.options
        moisture_sensor = opts.get(CONF_MOISTURE_SENSOR)
        if moisture_sensor:
            try:
                current = float(self.hass.states.get(moisture_sensor).state)
                if current >= float(opts.get(CONF_TARGET_MOISTURE, DEFAULT_TARGET_MOISTURE)):
                    return "Boden feucht genug"
            except (ValueError, AttributeError):
                pass

        if not garten:
            return "Kein Garten"
        if not garten.get_giess_ok():
            return "Heute nicht nötig"

        start_time = self._get_zone_start_time()
        if not start_time:
            return "Keine Startzeit"
        if now().time() < start_time:
            return f"{start_time.strftime('%H:%M')} Uhr"
        # Zeit >= Startzeit
        if not garten.get_wind_ok() and not self.options.get(CONF_IGNORE_WIND, DEFAULT_IGNORE_WIND):
            return "Wind zu stark"
        if not garten.get_solar_ok():
            return "Wartet auf weniger Sonne"
        return "Jetzt"

class ManuelleZoneCoordinator(DataUpdateCoordinator):
    """Manuell-Zone: einfacher Ventil-Schalter mit Brunnen-Monitoring."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_manuell")
        self._config_entry = config_entry
        self._state: str = STATE_IDLE
        self._in_brunnen_pause: bool = False
        self._was_open_before_pause: bool = False
        self._flow_value_at_start: float = 0.0
        self._monitor_task: asyncio.Task | None = None
        self._block_remaining_s: float = 0.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def block_remaining_s(self) -> float:
        return self._block_remaining_s

    @property
    def options(self) -> dict:
        merged = dict(self._config_entry.data)
        merged.update(self._config_entry.options)
        return merged

    def get_garten(self) -> "GartenCoordinator | None":
        parent_id = self.options.get(CONF_PARENT_ENTRY_ID)
        if not parent_id:
            return None
        coord = self.hass.data.get(DOMAIN, {}).get(parent_id)
        return coord if isinstance(coord, GartenCoordinator) else None

    async def async_setup(self) -> bool:
        self._state = STATE_IDLE
        return True

    async def async_shutdown(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        await self._async_valve_off()

    async def async_open(self) -> None:
        """Ventil öffnen."""
        if self._state in (STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE):
            return
        garten = self.get_garten()
        self._flow_value_at_start = garten.flow_counter if garten else 0.0
        self._state = STATE_MANUELL_OPEN
        self._in_brunnen_pause = False
        await self._async_valve_on()
        if self._has_flow_sensor():
            self._monitor_task = self.hass.async_create_task(self._async_monitor_brunnen())
        self.async_update_listeners()

    async def async_close(self) -> None:
        """Ventil schließen."""
        self._state = STATE_IDLE
        self._in_brunnen_pause = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        await self._async_valve_off()
        self.async_update_listeners()

    async def async_pause_for_brunnen(self) -> None:
        """Brunnenpause – Ventil zu, Zustand merken."""
        self._was_open_before_pause = self._state == STATE_MANUELL_OPEN
        if self._was_open_before_pause:
            self._state = STATE_MANUELL_PAUSE
            self._in_brunnen_pause = True
            await self._async_valve_off()
            self.async_update_listeners()

    async def async_resume_after_brunnen(self) -> None:
        """Nach Brunnenpause: wenn vorher offen, wieder öffnen."""
        self._in_brunnen_pause = False
        if self._was_open_before_pause and self._state == STATE_MANUELL_PAUSE:
            self._state = STATE_MANUELL_OPEN
            await self._async_valve_on()
            self.async_update_listeners()

    async def _async_valve_on(self) -> None:
        garten = self.get_garten()
        if garten:
            await garten.async_main_pump_on()
        valve = self.options.get(CONF_PUMP_SWITCH)
        if valve:
            await self.hass.services.async_call(
                valve.split(".")[0], "turn_on", {"entity_id": valve}, blocking=True
            )

    async def _async_valve_off(self) -> None:
        valve = self.options.get(CONF_PUMP_SWITCH)
        if valve:
            await self.hass.services.async_call(
                valve.split(".")[0], "turn_off", {"entity_id": valve}, blocking=True
            )
        garten = self.get_garten()
        if garten:
            await garten.async_main_pump_off(exclude=self)

    def _has_flow_sensor(self) -> bool:
        """Prueft ob ein Durchflussmesser fuer diese Manuell-Zone konfiguriert ist."""
        return bool(self.options.get(CONF_FLOW_SENSOR))

    async def _async_monitor_brunnen(self) -> None:
        """Ueberwacht Durchfluss waehrend Ventil offen ist, loest Brunnenpause aus."""
        garten = self.get_garten()
        if not garten:
            return
        try:
            while self._state in (STATE_MANUELL_OPEN, STATE_MANUELL_PAUSE):
                await asyncio.sleep(5)
                if self._state != STATE_MANUELL_OPEN:
                    continue
                flow_since = garten.get_flow_since(self._flow_value_at_start)
                if flow_since >= garten.get_flow_pause_liters():
                    pause_min = garten.get_pause_duration()
                    await self.async_pause_for_brunnen()
                    await self._async_notify(
                        message=f"Brunnenpause {pause_min:.0f} Min. ({flow_since:.0f}L gezogen)."
                    )
                    pause_s = pause_min * 60
                    elapsed = 0.0
                    self._block_remaining_s = pause_s
                    self.async_update_listeners()
                    while elapsed < pause_s and self._state == STATE_MANUELL_PAUSE:
                        await asyncio.sleep(1)
                        elapsed += 1
                        self._block_remaining_s = max(0.0, pause_s - elapsed)
                        self.async_update_listeners()
                    self._block_remaining_s = 0.0
                    if self._state != STATE_MANUELL_PAUSE:
                        continue
                    self._flow_value_at_start = garten.flow_counter
                    await self.async_resume_after_brunnen()
                    await self._async_notify(message="Brunnen erholt, weiter.")
        except asyncio.CancelledError:
            pass

    async def _async_notify(self, message: str = "") -> None:
        instance_name = self.options.get(CONF_INSTANCE_NAME, "Manuell")
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification", "create",
                {"title": instance_name, "message": message,
                 "notification_id": f"brunnen_bewasserung_{self._config_entry.entry_id}"},
            )
        )
