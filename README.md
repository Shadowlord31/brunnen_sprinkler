# 💧 Brunnen Bewässerung — Home Assistant Custom Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/github/v/release/Shadowlord31/brunnen_sprinkler)](https://github.com/Shadowlord31/brunnen_sprinkler/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🇩🇪 [Deutsche Version weiter unten](#-brunnen-bewässerung--home-assistant-custom-integration-1)

A smart garden irrigation controller for Home Assistant, designed for well-based pump systems. Supports automatic scheduling based on soil moisture and solar radiation, block/pause cycles for pump protection, wind holds, water level monitoring, and full notification support.

---

## Features

- **Automatic mode** — starts at a configurable earliest time when solar radiation is low and soil moisture is below target
- **Manual mode** — start immediately by toggling the irrigation switch
- **Block/pause cycles** — splits runtime into blocks with pauses to protect the well pump
- **Wind hold** — pauses irrigation when wind speed exceeds threshold, resumes automatically
- **Water level sensor** — time-based or sensor-based pump protection
- **Persistent daily tracking** — "already watered today" survives HA restarts; reset via button
- **Live countdown sensor** — counts down the current block or pause in real time (seconds)
- **Zone chaining** — trigger the next integration instance when a zone finishes
- **Configurable notifications** — choose any `notify.*` entity or `script.*`; each event individually toggleable
- **Reset button** — clears the daily watering lock instantly

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/Shadowlord31/brunnen_sprinkler` as **Integration**
3. Search for "Brunnen Bewässerung" and install
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → Brunnen Bewässerung**

### Manual

Copy the `custom_components/brunnen_bewasserung` folder into your `config/custom_components/` directory and restart.

---

## Configuration

Setup is done via the UI config flow in 3 steps.

**Step 1 — Sensors & Zone Chaining**

| Field | Description |
|---|---|
| Next zone (optional) | Entry ID of the next irrigation instance to trigger after this zone finishes |
| Water level sensor (optional) | Sensor entity for well water level (%) |
| Pump off below (%) | Pause when water level drops below this value |
| Pump on above (%) | Resume when water level recovers above this value |
| Max wait time (min) | Abort if water level does not recover within this time |

**Step 2 — Settings**

| Field | Description |
|---|---|
| Pump switch | `switch.*` or `input_boolean.*` entity controlling the pump |
| Soil moisture sensor | Sensor entity for soil moisture (%) |
| Wind speed sensor (optional) | Wind speed in km/h |
| Wind gust sensor (optional) | Gust speed in km/h |
| Wind threshold (km/h) | Pause irrigation above this wind speed |
| Target soil moisture (%) | Run until this moisture level is reached |
| Seconds per percent | Calibration: pump seconds per 1% moisture increase |
| Min runtime (min) | Minimum irrigation duration |
| Max runtime (min) | Maximum irrigation duration cap |
| Block duration (min) | Watering block length before each pause |
| Pause duration (min) | Rest time between blocks |
| Min remainder block (min) | Merge small remainders into the last block |
| Solar threshold (W/m²) | Only start when solar radiation is below this value |
| Earliest start time | Do not start before this time of day |
| Notify service (optional) | `notify.*` entity or `script.*` for notifications |
| Notify title (optional) | Custom notification title |

**Step 3 — Notifications**

Each event can be individually enabled or disabled: irrigation started, finished, block pause, manual stop, wind hold/cleared, water level low/recovered, next zone triggered, soil already sufficient.

---

## Entities

| Entity | Type | Description |
|---|---|---|
| `sensor.INSTANCE_status` | Sensor | `idle` / `watering` / `pausing` / `wind_hold` / `waiting_water` |
| `sensor.INSTANCE_nachster_start` | Sensor | Next scheduled start or current status text |
| `sensor.INSTANCE_restzeit` | Sensor | Total remaining runtime in minutes |
| `sensor.INSTANCE_aktuelle_etappe` | Sensor | Live countdown of current block or pause (seconds) |
| `sensor.INSTANCE_pause_modus` | Sensor | Pause mode: time-based or sensor-based |
| `binary_sensor.INSTANCE_bewasserung_aktiv` | Binary sensor | `on` while watering |
| `binary_sensor.INSTANCE_pause_aktiv` | Binary sensor | `on` during pump pause |
| `binary_sensor.INSTANCE_wind_pause_aktiv` | Binary sensor | `on` during wind hold |
| `switch.INSTANCE_automatikmodus` | Switch | Enable/disable automatic scheduling |
| `switch.INSTANCE_bewasserung_aktiv` | Switch | Manual start trigger (auto mode off) |
| `number.INSTANCE_*` | Numbers | All configurable thresholds and durations |
| `time.INSTANCE_fruhestzeit_start` | Time | Earliest allowed start time |
| `button.INSTANCE_heute_zurucksetzen` | Button | Reset today's watering lock |

`INSTANCE` = your configured instance name, e.g. `garten`

---

## Services

| Service | Parameter | Description |
|---|---|---|
| `brunnen_bewasserung.start` | `entry_id` | Force start (ignores daily lock and moisture check) |
| `brunnen_bewasserung.stop` | `entry_id` | Stop irrigation immediately |
| `brunnen_bewasserung.skip_today` | `entry_id` | Mark today as already watered |

---

## How It Works

**Automatic mode:** Every minute the integration checks: auto mode on, time ≥ earliest start, solar < threshold, soil moisture < target, not already watered today. If all conditions are met it calculates runtime `(target − current) × seconds_per_percent`, splits it into blocks, and starts the cycle. The daily lock is only set after a **complete** run — manual stops do not count.

**Block/pause cycle:** Runtime is split into blocks (e.g. 15 min on, 15 min off) to protect well pumps that need recovery time. Pause mode is either time-based or driven by a water level sensor.

**Wind hold:** If wind or gusts exceed the threshold during watering, the pump stops and waits. Once wind drops below threshold, watering resumes automatically.

---

## Requirements

- Home Assistant 2024.1 or newer
- HACS for easy installation
- A pump controlled by any `switch.*` or `input_boolean.*` entity
- Optional: soil moisture sensor, solar radiation sensor, wind sensors, water level sensor

---

## License

MIT — see [LICENSE](LICENSE)

---
---

# 💧 Brunnen Bewässerung — Home Assistant Custom Integration

> 🇬🇧 [English version above](#-brunnen-bewässerung--home-assistant-custom-integration)

Eine smarte Gartenbewässerungssteuerung für Home Assistant, entwickelt für brunnenbasierte Pumpensysteme. Unterstützt automatische Planung basierend auf Bodenfeuchte und Solarstrahlung, Block-/Pausenzyklen zum Pumpenschutz, Windpausen, Wasserstandsüberwachung und vollständige Benachrichtigungen.

---

## Funktionen

- **Automatikmodus** — startet zur konfigurierten Frühestzeit wenn Solar niedrig und Bodenfeuchte unter Zielwert
- **Manueller Modus** — sofortiger Start durch Einschalten des Bewässerungsschalters
- **Block-/Pausenzyklen** — teilt Laufzeit in Blöcke mit Pausen zum Schutz der Brunnenpumpe
- **Windpause** — stoppt Bewässerung bei zu hoher Windgeschwindigkeit, setzt automatisch fort
- **Wasserstandssensor** — zeitbasierter oder sensorbasierter Pumpenschutz
- **Persistente Tageserfassung** — überlebt HA-Neustarts; Reset per Button
- **Live-Countdown-Sensor** — zählt aktuellen Block oder Pause sekündlich herunter
- **Zonenkettung** — nächste Integrationsinstanz wird nach Abschluss einer Zone getriggert
- **Konfigurierbare Benachrichtigungen** — beliebiger `notify.*` oder `script.*` Dienst; jedes Ereignis einzeln schaltbar
- **Reset-Button** — setzt Tagessperre sofort zurück

---

## Installation

### Via HACS (empfohlen)

1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories
2. `https://github.com/Shadowlord31/brunnen_sprinkler` als **Integration** hinzufügen
3. Nach "Brunnen Bewässerung" suchen und installieren
4. Home Assistant neu starten
5. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Brunnen Bewässerung**

### Manuell

Den Ordner `custom_components/brunnen_bewasserung` in `config/custom_components/` kopieren und HA neu starten.

---

## Konfiguration

Die Einrichtung erfolgt über den UI-Konfigurationsflow in 3 Schritten.

**Schritt 1 — Optionale Sensoren & Verkettung**

| Feld | Beschreibung |
|---|---|
| Nächste Zone (optional) | Entry-ID der nächsten Instanz die nach dieser Zone gestartet wird |
| Wasserstand-Sensor (optional) | Sensor-Entity für Brunnen-Wasserstand (%) |
| Pumpe AUS unter (%) | Bewässerung pausieren wenn Wasserstand diesen Wert unterschreitet |
| Pumpe AN über (%) | Fortsetzen wenn Wasserstand sich erholt hat |
| Max. Wartezeit (Min) | Abbruch wenn Wasserstand sich nicht innerhalb dieser Zeit erholt |

**Schritt 2 — Einstellungen**

| Feld | Beschreibung |
|---|---|
| Pumpenschalter | `switch.*` oder `input_boolean.*` Entity für die Pumpe |
| Bodenfeuchte-Sensor | Sensor-Entity für Bodenfeuchte (%) |
| Windgeschwindigkeits-Sensor (optional) | Windgeschwindigkeit in km/h |
| Windböen-Sensor (optional) | Böengeschwindigkeit in km/h |
| Wind-Schwellwert (km/h) | Ab dieser Windgeschwindigkeit Bewässerung pausieren |
| Ziel-Bodenfeuchte (%) | Bewässerung läuft bis dieser Wert erreicht ist |
| Sekunden pro Prozent | Kalibrierung: Sekunden Pumpenlaufzeit pro 1% Bodenfeuchte-Anstieg |
| Minimale Laufzeit (Min) | Mindest-Bewässerungsdauer |
| Maximale Laufzeit (Min) | Maximale Bewässerungsdauer |
| Block-Dauer (Min) | Bewässerungsblocklänge vor jeder Pause |
| Pausen-Dauer (Min) | Ruhezeit zwischen Blöcken |
| Min. Restblock (Min) | Kleine Restzeit auf letzten Block draufrechnen statt Mini-Block |
| Solar-Schwellwert (W/m²) | Nur starten wenn Solar unter diesem Wert liegt |
| Frühestzeit | Nicht vor dieser Uhrzeit starten |
| Benachrichtigungsdienst (optional) | `notify.*` Entity oder `script.*` |
| Benachrichtigungstitel (optional) | Eigener Titel für Benachrichtigungen |

**Schritt 3 — Benachrichtigungen**

Jedes Ereignis einzeln schaltbar: Bewässerung gestartet, abgeschlossen, Block-Pause, manuell gestoppt, Wind-Pause/nachgelassen, Wasserstand niedrig/erholt, nächste Zone, Boden bereits feucht.

---

## Entities

| Entity | Typ | Beschreibung |
|---|---|---|
| `sensor.INSTANZ_status` | Sensor | `idle` / `watering` / `pausing` / `wind_hold` / `waiting_water` |
| `sensor.INSTANZ_nachster_start` | Sensor | Nächster Start oder aktueller Statustext |
| `sensor.INSTANZ_restzeit` | Sensor | Gesamte Restlaufzeit in Minuten |
| `sensor.INSTANZ_aktuelle_etappe` | Sensor | Live-Countdown des aktuellen Blocks oder der Pause (Sekunden) |
| `sensor.INSTANZ_pause_modus` | Sensor | Pausenmodus: Zeitbasiert oder Sensor |
| `binary_sensor.INSTANZ_bewasserung_aktiv` | Binary Sensor | An während Bewässerung läuft |
| `binary_sensor.INSTANZ_pause_aktiv` | Binary Sensor | An während Pumpenpause |
| `binary_sensor.INSTANZ_wind_pause_aktiv` | Binary Sensor | An während Windpause |
| `switch.INSTANZ_automatikmodus` | Schalter | Automatik-Modus ein-/ausschalten |
| `switch.INSTANZ_bewasserung_aktiv` | Schalter | Manueller Start-Trigger (wenn Automatik aus) |
| `number.INSTANZ_*` | Zahlen | Alle konfigurierbaren Schwellwerte und Dauern |
| `time.INSTANZ_fruhestzeit_start` | Zeit | Früheste erlaubte Startzeit |
| `button.INSTANZ_heute_zurucksetzen` | Button | Tagessperre zurücksetzen |

`INSTANZ` = konfigurierter Instanzname, z.B. `garten`

---

## Services

| Service | Parameter | Beschreibung |
|---|---|---|
| `brunnen_bewasserung.start` | `entry_id` | Sofortiger Start (ignoriert Tagessperre und Feuchtecheck) |
| `brunnen_bewasserung.stop` | `entry_id` | Bewässerung sofort stoppen |
| `brunnen_bewasserung.skip_today` | `entry_id` | Heute als bereits gegossen markieren |

---

## Funktionsweise

**Automatikmodus:** Jede Minute prüft die Integration: Automatik an, Zeit ≥ Frühestzeit, Solar < Schwellwert, Bodenfeuchte < Zielwert, heute noch nicht gegossen. Bei Erfüllung aller Bedingungen wird die Laufzeit berechnet, in Blöcke aufgeteilt und der Zyklus gestartet. Die Tagessperre wird nur nach einem **vollständigen** Durchlauf gesetzt — manueller Abbruch zählt nicht.

**Block-/Pausenzyklus:** Die Laufzeit wird in Blöcke aufgeteilt um Brunnenpumpen mit Erholungsbedarf zu schützen. Pausenmodus ist zeitbasiert oder sensorgesteuert.

**Windpause:** Überschreitet Wind oder Böen den Schwellwert während der Bewässerung, stoppt die Pumpe und wartet. Sobald der Wind nachlässt, wird automatisch fortgesetzt.

---

## Voraussetzungen

- Home Assistant 2024.1 oder neuer
- HACS für einfache Installation
- Pumpe gesteuert durch `switch.*` oder `input_boolean.*` Entity
- Optional: Bodenfeuchte-Sensor, Solarstrahlungs-Sensor, Wind-Sensoren, Wasserstand-Sensor

---

## Lizenz

MIT — siehe [LICENSE](LICENSE)
