# brunnen_bewasserung – Custom Integration
## Architekturplan & Aider/Cline Prompts

---

## Übersicht

**Domain:** `brunnen_bewasserung`
**Ziel:** Vollständige Home Assistant Custom Integration für Brunnen-basierte Bewässerung mit:
- Block/Pause-Logik (zeitbasiert ODER sensorbasiert über Wasserstand)
- Instanz-Verkettung (Zonen-Sequenz: Zone 1 → Zone 2 → ...)
- Wind-Schutz, Solar-Trigger, eigenem Notify-Service
- Mehrere Instanzen (eine pro Zone/Bereich) gleichzeitig betreibbar

**Logik:** Komplett in Python (kein YAML), HACS-kompatibel, Multi-Instanz-fähig.

---

## Neue Konzepte gegenüber v1

### 1. Instanz-Verkettung (Zonen-Sequenz)

Jede Instanz kann eine "Nächste Zone" kennen. Nach Abschluss der eigenen Bewässerung
startet sie automatisch die nächste Instanz. Damit lässt sich eine beliebig lange
Kette oder ein Ring von Zonen definieren:

```
Garten → Hochbeet → Kräuter → (Ende oder zurück zu Garten)
```

- Im Config Flow: optionales Feld "Nächste Zone" (Dropdown aller anderen brunnen_bewasserung Instanzen)
- Der Coordinator ruft nach Abschluss den "start"-Service der nächsten Instanz auf
- Jede Instanz kennt nur ihren direkten Nachfolger (keine globale Steuerung nötig)
- Kreise sind erlaubt (Ring-Bewässerung), werden aber durch die Tagessperre von selbst begrenzt

### 2. Wasserstand-Sensor (ersetzt oder ergänzt Block/Pause-Logik)

Statt fester Zeitblöcke kann ein Wasserstand-Sensor die Pause steuern:

**Zeitbasierter Modus (Standard):** 15 Min Wasser → 15 Min Pause → 15 Min Wasser → ...
**Sensorbasierter Modus:** Pumpe läuft → Wasserstand fällt unter Schwellwert_low → Pumpe aus
→ Wasserstand steigt über Schwellwert_high → Pumpe wieder an → weiter

Konfiguration:
- `water_level_sensor`: optional (wenn leer = Zeitbasierter Modus)
- `water_level_low`: Schwellwert für "Pumpe aus" (z.B. 20%)
- `water_level_high`: Schwellwert für "Pumpe wieder an" (z.B. 60%)
- `water_level_timeout`: Max. Wartezeit in Minuten (Sicherheit falls Sensor ausfällt)

---

## Dateistruktur

```
custom_components/brunnen_bewasserung/
├── __init__.py
├── manifest.json
├── hacs.json
├── config_flow.py
├── const.py
├── coordinator.py
├── sensor.py
├── binary_sensor.py
├── switch.py
├── number.py
├── datetime_entity.py
├── services.py
├── services.yaml
├── strings.json
└── translations/
    ├── de.json
    └── en.json
```

---

## Präambel (IMMER vor jeden Aider-Prompt stellen)

```
WICHTIG: Ändere NUR die Stellen die ich explizit nenne.
Lösche NICHTS was bereits vorhanden ist.
Füge NUR hinzu was ich beschreibe.
Schreibe KEINE komplette Datei neu wenn sie bereits existiert.
Verändere KEINE Imports die bereits vorhanden sind.
Verändere KEINE anderen Funktionen oder Klassen.
```

---

## PROMPT 1 – const.py + manifest.json + hacs.json

### Dateien: `const.py`, `manifest.json`, `hacs.json`
### Tool: Aider oder Cline (neue Dateien, unkritisch)

```
Erstelle drei neue Dateien für eine Home Assistant Custom Integration namens "brunnen_bewasserung".

### const.py
Definiere folgende Konstanten:

DOMAIN = "brunnen_bewasserung"

# Pflicht-Sensoren
CONF_INSTANCE_NAME = "instance_name"
CONF_PUMP_SWITCH = "pump_switch"
CONF_MOISTURE_SENSOR = "moisture_sensor"
CONF_SOLAR_SENSOR = "solar_sensor"
CONF_WIND_SPEED_SENSOR = "wind_speed_sensor"
CONF_WIND_GUST_SENSOR = "wind_gust_sensor"

# Gieß-Assistent (optional)
CONF_GIESS_ENABLED = "giess_assistent_enabled"
CONF_GIESS_SENSOR = "giess_assistent_sensor"

# Instanz-Verkettung (optional)
CONF_NEXT_ZONE_ENTRY_ID = "next_zone_entry_id"  # entry_id der nächsten Instanz, oder None

# Wasserstand-Sensor (optional, ersetzt Block/Pause wenn gesetzt)
CONF_WATER_LEVEL_SENSOR = "water_level_sensor"
CONF_WATER_LEVEL_LOW = "water_level_low"
CONF_WATER_LEVEL_HIGH = "water_level_high"
CONF_WATER_LEVEL_TIMEOUT = "water_level_timeout"

# Standardwerte
DEFAULT_TARGET_MOISTURE = 45.0
DEFAULT_SECONDS_PER_PERCENT = 395.0
DEFAULT_MIN_RUNTIME = 5.0
DEFAULT_MAX_RUNTIME = 100.0
DEFAULT_BLOCK_DURATION = 15.0
DEFAULT_PAUSE_DURATION = 15.0
DEFAULT_WIND_SPEED_LIMIT = 15.0
DEFAULT_WIND_GUST_LIMIT = 25.0
DEFAULT_SOLAR_THRESHOLD = 400.0
DEFAULT_EARLIEST_START = "17:30"
DEFAULT_WATER_LEVEL_LOW = 20.0
DEFAULT_WATER_LEVEL_HIGH = 60.0
DEFAULT_WATER_LEVEL_TIMEOUT = 30.0

# State-Konstanten
STATE_IDLE = "idle"
STATE_WATERING = "watering"
STATE_PAUSING = "pausing"
STATE_WIND_HOLD = "wind_hold"
STATE_WAITING_WATER = "waiting_water"  # NEU: wartet auf Brunnen-Erholung per Sensor

# Attribute
ATTR_REMAINING_S = "remaining_seconds"
ATTR_CURRENT_BLOCK = "current_block"
ATTR_TOTAL_BLOCKS = "total_blocks"
ATTR_NEXT_START = "next_start"
ATTR_LAST_RUN = "last_run"
ATTR_NEXT_ZONE = "next_zone"
ATTR_PAUSE_MODE = "pause_mode"  # "time" oder "sensor"

### manifest.json
{
  "domain": "brunnen_bewasserung",
  "name": "Brunnen Bewässerung",
  "version": "1.0.0",
  "documentation": "https://github.com/Shadowlord31/brunnen-bewasserung",
  "issue_tracker": "https://github.com/Shadowlord31/brunnen-bewasserung/issues",
  "requirements": [],
  "dependencies": [],
  "codeowners": ["@Shadowlord31"],
  "iot_class": "local_push",
  "config_flow": true
}

### hacs.json
{
  "name": "Brunnen Bewässerung",
  "content_in_root": false,
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

---

## PROMPT 2 – config_flow.py

### Datei: `config_flow.py`
### Tool: Cline empfohlen (komplex, viel Kontext)
### Voraussetzung: `const.py` ist fertig

```
Erstelle config_flow.py für die Home Assistant Custom Integration "brunnen_bewasserung".
Importiere aus const.py alle CONF_* und DEFAULT_* Konstanten.

Der Config Flow hat DREI Schritte:

SCHRITT 1 – user (Pflicht-Entities + Instanzname):
- instance_name: TextSelector, Default "Garten"
  (wird als Geräte-Name und Entity-Prefix verwendet)
- pump_switch: Entity-Selector, Domain "switch"
- moisture_sensor: Entity-Selector, Domain "sensor"
- solar_sensor: Entity-Selector, Domain "sensor"
- wind_speed_sensor: Entity-Selector, Domain "sensor"
- wind_gust_sensor: Entity-Selector, Domain "sensor"
- giess_assistent_enabled: Boolean, Default True
- giess_assistent_sensor: Entity-Selector, Domain "binary_sensor", optional

SCHRITT 2 – optional_sensors (Optionale Sensoren + Verkettung):
- next_zone_entry_id: SelectSelector mit allen anderen brunnen_bewasserung
  Config-Entry-IDs als Optionen (Anzeige: entry.title, Wert: entry.entry_id).
  Label: "Nächste Zone (optional)". Default: leer/None.
- water_level_sensor: Entity-Selector, Domain "sensor", optional
  Label: "Wasserstand-Sensor (optional, ersetzt Block/Pause-Zeitlogik)"
- water_level_low: NumberSelector min=0 max=100 step=1 unit="%"
  Label: "Wasserstand: Pumpe AUS unter" Default: 20
- water_level_high: NumberSelector min=0 max=100 step=1 unit="%"
  Label: "Wasserstand: Pumpe AN über" Default: 60
- water_level_timeout: NumberSelector min=5 max=120 step=5 unit="min"
  Label: "Max. Wartezeit auf Brunnen-Erholung" Default: 30

SCHRITT 3 – settings (Standardwerte):
- target_moisture: NumberSelector min=10 max=100 step=1 unit="%"
- seconds_per_percent: NumberSelector min=60 max=600 step=5 unit="s/%"
- min_runtime: NumberSelector min=1 max=30 step=1 unit="min"
- max_runtime: NumberSelector min=10 max=180 step=5 unit="min"
- block_duration: NumberSelector min=5 max=60 step=1 unit="min"
  (nur relevant wenn KEIN water_level_sensor gesetzt)
- pause_duration: NumberSelector min=5 max=60 step=1 unit="min"
  (nur relevant wenn KEIN water_level_sensor gesetzt)
- wind_speed_limit: NumberSelector min=5 max=50 step=1 unit="km/h"
- wind_gust_limit: NumberSelector min=5 max=80 step=1 unit="km/h"
- solar_threshold: NumberSelector min=50 max=1000 step=10 unit="W/m²"
- earliest_start: TimeSelector

Validierung:
- Pflicht-Entities müssen in HA existieren (hass.states.get != None)
- water_level_low muss kleiner als water_level_high sein
- next_zone_entry_id darf nicht die eigene entry_id sein (kein Selbst-Loop)

OptionsFlow: Gleiche Felder wie Schritt 2+3 für nachträgliche Anpassung.

Titel des Config Entries: f"Brunnen Bewässerung – {instance_name}"
```

---

## PROMPT 3 – coordinator.py Grundgerüst

### Datei: `coordinator.py`
### Tool: Cline empfohlen
### Voraussetzung: const.py fertig

```
Erstelle coordinator.py für die Home Assistant Custom Integration "brunnen_bewasserung".
Importiere aus homeassistant.helpers.update_coordinator: DataUpdateCoordinator
Importiere aus const.py alle Konstanten.

Erstelle die Klasse BrunnenBewasserungCoordinator(DataUpdateCoordinator).

__init__ Parameter:
- hass: HomeAssistant
- config_entry: ConfigEntry

Initialisiere folgende instance-Variablen (alle private mit _):
_state: str = STATE_IDLE
_remaining_s: float = 0.0
_block_remaining_s: float = 0.0
_current_block: int = 0
_total_blocks: int = 0
_last_run: date | None = None
_auto_mode: bool = True
_enabled: bool = True
_pause_mode: str = "time"          # "time" oder "sensor"
_watering_task: asyncio.Task | None = None
_water_level_unsub: Callable | None = None
_wind_unsub: Callable | None = None
_time_unsub: Callable | None = None

Properties (read-only) für alle _-Variablen.

Methoden als Platzhalter (pass):
- async async_setup() -> bool
- async async_shutdown()
- async async_start_watering(force: bool = False) -> bool
- async async_stop_watering()
- async async_skip_today()
- async _async_run_watering_cycle()
- async _async_run_block(duration_s: float)
- async _async_run_pause_time()
- async _async_run_pause_sensor()
- async _async_trigger_next_zone()
- async _async_check_wind(event)
- async _async_background_check(now)
- async _async_notify(title: str, message: str)
- def _calculate_runtime() -> float
- def _should_start_auto() -> bool
- def _get_next_start_info() -> str
- def _has_water_level_sensor() -> bool
- def _get_next_zone_coordinator() -> "BrunnenBewasserungCoordinator | None"
```

---

## PROMPT 4 – coordinator.py Bewässerungslogik

### Datei: `coordinator.py` (ERGÄNZEN, nicht neu schreiben!)
### Voraussetzung: Prompt 3 fertig

```
WICHTIG: Ändere NUR die Methoden die ich explizit nenne. Lösche NICHTS anderes.

### _has_water_level_sensor() -> bool
Gibt True zurück wenn options.get(CONF_WATER_LEVEL_SENSOR) nicht None/leer ist.

### _get_next_zone_coordinator() -> BrunnenBewasserungCoordinator | None
next_id = options.get(CONF_NEXT_ZONE_ENTRY_ID)
Falls None oder leer: return None
Falls next_id in hass.data[DOMAIN]: return hass.data[DOMAIN][next_id]
Sonst: return None

### _calculate_runtime() -> float
Liest moisture_sensor, target_moisture, seconds_per_percent, min_runtime, max_runtime.
Berechnet dauer_s = (ziel - aktuell) * sek_pro_prozent.
Gibt max(min_s, min(dauer_s, max_s)) zurück.
Falls aktuell >= ziel: return 0.0

### _should_start_auto() -> bool
Prüft ALLE dieser Bedingungen:
1. _state == STATE_IDLE
2. _auto_mode == True
3. _enabled == True
4. _last_run != date.today()
5. now().time() >= earliest_start als time-Objekt
6. Solar-Sensor float < solar_threshold
7. Falls giess_enabled: binary_sensor.state == "on"
8. Bodenfeuchte < target_moisture
Gibt True zurück nur wenn alle erfüllt.

### async_start_watering(force=False) -> bool
1. Falls _state != STATE_IDLE: return False
2. runtime_s = _calculate_runtime()
3. Falls runtime_s <= 0: notify + return False
4. Falls not force: Tagessperre prüfen (_last_run == today → return False)
5. _pause_mode = "sensor" falls _has_water_level_sensor() else "time"
6. block_s = min(runtime_s, block_duration_s)
7. _remaining_s = runtime_s - block_s
8. _total_blocks = ceil(runtime_s / block_s)
9. _current_block = 1
10. _last_run = date.today()
11. _watering_task = hass.async_create_task(_async_run_watering_cycle())
12. return True

### _async_run_watering_cycle()
Loop:
1. _state = STATE_WATERING; self.async_update_listeners()
2. Pumpe AN
3. await _async_run_block(aktueller_block_s)
4. Pumpe AUS; self.async_update_listeners()
5. Falls _remaining_s <= 0:
   _state = STATE_IDLE
   await _async_notify("Bewässerung abgeschlossen")
   await _async_trigger_next_zone()
   break
6. Falls _pause_mode == "sensor":
   await _async_run_pause_sensor()
   else:
   await _async_run_pause_time()
7. _current_block += 1
8. block_s = min(_remaining_s, block_duration_s)
9. _remaining_s -= block_s
10. Zurück zu 1.

### _async_run_block(duration_s)
await asyncio.sleep(duration_s)

### _async_run_pause_time()
_state = STATE_PAUSING; self.async_update_listeners()
pause_s = options[CONF_PAUSE_DURATION] * 60
await _async_notify(f"Block beendet. Pause {pause_s//60} Min. Restzeit: {_remaining_s//60:.0f} Min.")
await asyncio.sleep(pause_s)

### _async_run_pause_sensor()
_state = STATE_WAITING_WATER; self.async_update_listeners()
low = options[CONF_WATER_LEVEL_LOW]
high = options[CONF_WATER_LEVEL_HIGH]
timeout_s = options[CONF_WATER_LEVEL_TIMEOUT] * 60
sensor = options[CONF_WATER_LEVEL_SENSOR]

await _async_notify(f"Wasserstand niedrig. Warte auf Erholung (Ziel: >{high}%).")

# Warte maximal timeout_s auf Erholung
start = datetime.now()
while True:
    level = float(hass.states.get(sensor).state)
    if level >= high:
        await _async_notify(f"Wasserstand erholt ({level}%). Weiter mit nächstem Block.")
        break
    if (datetime.now() - start).seconds >= timeout_s:
        await _async_notify("Timeout: Wasserstand nicht erholt. Bewässerung abgebrochen.")
        await async_stop_watering()
        return
    await asyncio.sleep(30)  # alle 30s prüfen

### async_stop_watering()
Falls _watering_task: _watering_task.cancel()
Pumpe AUS
_state = STATE_IDLE
_remaining_s = 0
_current_block = 0
self.async_update_listeners()

### _async_trigger_next_zone()
next_coord = _get_next_zone_coordinator()
Falls next_coord und next_coord._state == STATE_IDLE:
    await _async_notify(f"Starte nächste Zone.")
    await next_coord.async_start_watering(force=True)
```

---

## PROMPT 5 – coordinator.py Wind-Logik + Notify + Setup

### Datei: `coordinator.py` (ERGÄNZEN)
### Voraussetzung: Prompt 4 fertig

```
WICHTIG: Ändere NUR die Methoden die ich nenne.

### async_setup()
1. Bestimme _pause_mode initial aus options (sensor oder time)
2. Wind-Listener: async_track_state_change_event auf [wind_speed, wind_gust]
3. Time-Listener: async_track_time_interval alle 5 Minuten
4. Falls water_level_sensor gesetzt: async_track_state_change_event auf
   water_level_sensor für Echtzeit-Überwachung während STATE_WATERING
   (wenn Level < low während Watering: sofort Pause einleiten)
5. return True

### async_shutdown()
Alle _unsub()-Callbacks aufrufen.
await async_stop_watering()

### _async_check_wind(event)
speed = float(hass.states.get(wind_speed_sensor).state)
gust = float(hass.states.get(wind_gust_sensor).state)

Falls _state == STATE_WATERING UND (speed > limit ODER gust > gust_limit):
  _state = STATE_WIND_HOLD
  _block_remaining_s = (verbleibende Zeit im aktuellen Block)
  Pumpe AUS
  await _async_notify(f"Wind-Pause: {speed:.1f} km/h / Böe {gust:.1f} km/h")

Falls _state == STATE_WIND_HOLD UND speed <= limit UND gust <= gust_limit:
  _state = STATE_WATERING
  Pumpe AN
  Restlichen Block weiterlaufen lassen (_block_remaining_s)
  await _async_notify("Wind nachgelassen. Bewässerung fortgesetzt.")

### _async_background_check(now)
Falls _should_start_auto():
    await async_start_watering()

### _async_notify(title: str = None, message: str)
Falls title None: title = f"Brunnen Bewässerung – {instance_name}"
Versuche script.master_notify_v1_1_0 aufzurufen:
  hass.services.async_call("script", "master_notify_v1_1_0", {
    "title": title, "message": message,
    "group_admins_enable": True, "group_family_enable": True,
    "alexa_enabled": False, "google_enabled": False, "critical_enabled": False
  }, blocking=False)
Falls Service nicht existiert (try/except):
  hass.components.persistent_notification.async_create(message, title=title)

### _get_next_start_info() -> str
Falls _state == STATE_WATERING: return "Läuft"
Falls _state == STATE_PAUSING: return f"Pause ({_remaining_s//60:.0f} Min Rest)"
Falls _state == STATE_WAITING_WATER: return "Wartet auf Brunnen"
Falls _state == STATE_WIND_HOLD: return "Wind-Pause"
Falls not _enabled: return "Deaktiviert"
Falls not _auto_mode: return "Manuell"
Falls _last_run == today: return "Heute schon gelaufen"
Falls Bodenfeuchte >= Ziel: return "Boden feucht genug"
Falls giess_enabled und giess_sensor off: return "Heute nicht nötig"
Berechne Frühestzeit → falls jetzt >= fruehestzeit und solar ok: return "Jetzt"
Falls jetzt >= fruehestzeit: return "Wartet auf Sonne"
return f"{fruehestzeit.strftime('%H:%M')} Uhr"
```

---

## PROMPT 6 – sensor.py + binary_sensor.py

### Dateien: `sensor.py`, `binary_sensor.py`
### Voraussetzung: coordinator.py fertig

```
Erstelle sensor.py und binary_sensor.py für brunnen_bewasserung.

Alle Entities bekommen DeviceInfo mit:
- identifiers: {(DOMAIN, entry.entry_id)}
- name: entry.options.get(CONF_INSTANCE_NAME, "Brunnen Bewässerung")
- manufacturer: "brunnen_bewasserung"

### sensor.py – 4 Sensoren:

1. BrunnenNextStartSensor
   - name: "Nächster Start"
   - unique_id: f"{entry.entry_id}_next_start"
   - icon: mdi:calendar-clock
   - state: coordinator._get_next_start_info()

2. BrunnenRemainingTimeSensor
   - name: "Restzeit"
   - unique_id: f"{entry.entry_id}_remaining"
   - native_unit: UnitOfTime.MINUTES
   - device_class: SensorDeviceClass.DURATION
   - state: round(coordinator._remaining_s / 60, 1)
   - extra_state_attributes:
     remaining_seconds, current_block, total_blocks,
     pause_mode: coordinator._pause_mode,
     next_zone: (title der nächsten Instanz oder None)

3. BrunnenStateSensor
   - name: "Status"
   - unique_id: f"{entry.entry_id}_state"
   - icon: dynamisch nach _state
     watering → mdi:sprinkler-variant
     pausing → mdi:pause-circle
     wind_hold → mdi:weather-windy
     waiting_water → mdi:water-off
     idle → mdi:sleep
   - state: coordinator._state

4. BrunnenPauseModeSensor
   - name: "Pause Modus"
   - unique_id: f"{entry.entry_id}_pause_mode"
   - icon: mdi:water-pump (sensor) oder mdi:timer (time)
   - state: "Sensor" wenn _pause_mode=="sensor" sonst "Zeitbasiert"

### binary_sensor.py – 3 Sensoren:

1. BrunnenIsWateringSensor
   - name: "Bewässerung aktiv"
   - device_class: BinarySensorDeviceClass.RUNNING
   - is_on: coordinator._state == STATE_WATERING

2. BrunnenIsPausingSensor
   - name: "Pause aktiv"
   - device_class: BinarySensorDeviceClass.RUNNING
   - is_on: coordinator._state in [STATE_PAUSING, STATE_WAITING_WATER]

3. BrunnenIsWindHoldSensor
   - name: "Wind-Pause aktiv"
   - device_class: BinarySensorDeviceClass.PROBLEM
   - is_on: coordinator._state == STATE_WIND_HOLD
```

---

## PROMPT 7 – switch.py + number.py + datetime_entity.py

### Dateien: `switch.py`, `number.py`, `datetime_entity.py`
### Voraussetzung: coordinator.py + sensor.py fertig

```
Erstelle switch.py, number.py und datetime_entity.py.
Alle Entities mit gleichem DeviceInfo wie in sensor.py.

### switch.py – 2 Switches:

1. BrunnenAutoModeSwitch
   - name: "Automatikmodus"
   - icon: mdi:auto-mode
   - is_on: coordinator._auto_mode
   - async_turn_on/off: coordinator._auto_mode setzen + async_update_listeners()

2. BrunnenEnabledSwitch
   - name: "Bewässerung aktiv"
   - icon: mdi:sprinkler
   - is_on: coordinator._enabled
   - async_turn_off: coordinator._enabled = False; await coordinator.async_stop_watering()

### number.py – 9 Number Entities:

Alle schreiben via hass.config_entries.async_update_entry in options.

- target_moisture: min=10 max=100 step=1 unit="%", icon=mdi:water-percent
- seconds_per_percent: min=60 max=600 step=5 unit="s/%", icon=mdi:timer-sand
- min_runtime: min=1 max=30 step=1 unit="min", icon=mdi:timer-outline
- max_runtime: min=10 max=180 step=5 unit="min", icon=mdi:timer-outline
- block_duration: min=5 max=60 step=1 unit="min", icon=mdi:timer-play
  (entity_category: EntityCategory.CONFIG, da nur bei Zeitbasiertem Modus relevant)
- pause_duration: min=5 max=60 step=1 unit="min", icon=mdi:timer-pause
  (entity_category: EntityCategory.CONFIG)
- solar_threshold: min=50 max=1000 step=10 unit="W/m²", icon=mdi:weather-sunny
- water_level_low: min=0 max=100 step=1 unit="%", icon=mdi:water-minus
  (entity_category: EntityCategory.CONFIG)
- water_level_high: min=0 max=100 step=1 unit="%", icon=mdi:water-plus
  (entity_category: EntityCategory.CONFIG)

### datetime_entity.py – 1 Time Entity:

BrunnenEarliestStartTime:
- name: "Frühestzeit Start"
- icon: mdi:clock-start
- platform: TimeEntity
- native_value: time aus options[CONF_EARLIEST_START]
- async_set_value: schreibt in options
```

---

## PROMPT 8 – __init__.py + services.py + services.yaml + Translations

### Dateien: `__init__.py`, `services.py`, `services.yaml`, Translations
### Voraussetzung: Alle anderen Dateien fertig

```
Erstelle __init__.py, services.py, services.yaml und Translations.

### __init__.py
PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "datetime"]

async_setup_entry(hass, entry):
1. Erstelle BrunnenBewasserungCoordinator(hass, entry)
2. await coordinator.async_setup()
3. hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
4. await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
5. await async_register_services(hass)
6. entry.async_on_unload(entry.add_update_listener(async_reload_entry))

async_unload_entry(hass, entry):
1. await coordinator.async_shutdown()
2. await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
3. hass.data[DOMAIN].pop(entry.entry_id)

async_register_services: nur registrieren falls noch nicht registriert
(hass.services.has_service(DOMAIN, "start") prüfen)

### services.py – 5 Services:

Alle Services bekommen einen optionalen "entry_id"-Parameter um die Ziel-Instanz
zu identifizieren. Falls nicht angegeben: erste verfügbare Instanz.

1. "start" – Startet Bewässerung sofort (force=True, ignoriert Tagessperre)
2. "stop" – Bricht Bewässerung/Pause ab
3. "skip_today" – Überspringt heutigen automatischen Lauf
4. "start_sequence" – Startet die gesamte Zonen-Kette ab dieser Instanz
   (ruft async_start_watering(force=True) auf, Verkettung übernimmt den Rest)
5. "notify" – Interner Notify-Service
   Parameter: title (string), message (string)
   Sendet über script.master_notify_v1_1_0 falls vorhanden,
   sonst persistent_notification als Fallback.

### services.yaml
start:
  description: "Startet die Bewässerung sofort (ignoriert Tagessperre)"
  fields:
    entry_id:
      description: "ID der Ziel-Instanz (optional)"
      example: "abc123def456"
stop:
  description: "Bricht die aktuelle Bewässerung/Pause ab"
  fields:
    entry_id:
      description: "ID der Ziel-Instanz (optional)"
skip_today:
  description: "Überspringt den heutigen automatischen Lauf"
  fields:
    entry_id:
      description: "ID der Ziel-Instanz (optional)"
start_sequence:
  description: "Startet die komplette Zonen-Sequenz ab dieser Instanz"
  fields:
    entry_id:
      description: "ID der Start-Instanz (optional)"
notify:
  description: "Interne Benachrichtigung"
  fields:
    title:
      description: "Titel"
      example: "Brunnen Bewässerung"
    message:
      description: "Nachrichtentext"
      example: "Bewässerung gestartet"

### translations/de.json
Übersetze alle Config-Flow-Labels, Step-Titel und Entity-Namen auf Deutsch.
Verwende diese Bezeichnungen:
- instance_name: "Zonenname"
- pump_switch: "Pumpen-Schalter"
- moisture_sensor: "Bodenfeuchtesensor"
- next_zone_entry_id: "Nächste Zone (optional)"
- water_level_sensor: "Wasserstand-Sensor (optional)"
- water_level_low: "Pumpe AUS unter (%) "
- water_level_high: "Pumpe AN über (%)"
- water_level_timeout: "Max. Wartezeit (Minuten)"
- block_duration: "Block-Dauer"
- pause_duration: "Pause-Dauer"

### translations/en.json
Englische Übersetzung aller Labels.
```

---

## Hinweise für Cline vs. Aider

### Aider (Kommandozeile)
- Immer Präambel voranstellen
- Nur eine Datei pro Session: `aider const.py`
- coordinator.py in 3 Sessions aufteilen (Prompts 3, 4, 5)
- Nach jedem Prompt: `git diff` prüfen

### Cline (VS Code)
- Kein Präambel nötig
- Kontext-Dateien mit "Add to context" explizit referenzieren
- Kann mehrere Dateien gleichzeitig sehen → coordinator.py + const.py zusammen öffnen
- Für Prompts 4+5: const.py + coordinator.py (bisheriger Stand) als Kontext

---

## Multi-Instanz Beispiel-Setup

```
Zone 1: "Garten"     → next_zone: Zone 2, moisture: sensor.gw1100_soilmoisture1
Zone 2: "Hochbeet"   → next_zone: Zone 3, moisture: sensor.hochbeet_feuchte
Zone 3: "Kräuter"    → next_zone: None (Ende der Kette)
```

Ablauf:
1. Zone 1 startet automatisch um 17:30 (Solar < 400)
2. Zone 1 fertig → triggert Zone 2
3. Zone 2 fertig → triggert Zone 3
4. Zone 3 fertig → Ende

---

## GitHub Repository Setup

```bash
# Repo: Shadowlord31/brunnen-bewasserung (public)
mkdir -p brunnen-bewasserung/custom_components/brunnen_bewasserung/translations
cd brunnen-bewasserung
git init
# Dateien erstellen (per Prompts oben)...
git add .
git commit -m "feat: initial brunnen_bewasserung integration v1.0.0"
git remote add origin https://github.com/Shadowlord31/brunnen-bewasserung.git
git push -u origin main
```

HACS-Anforderungen:
- `hacs.json` im Root des Repos
- `custom_components/brunnen_bewasserung/` als Unterordner
- `README.md` mit Installations- und Konfigurationsanleitung
- Mindestens ein GitHub Release mit Tag (z.B. `v1.0.0`)
