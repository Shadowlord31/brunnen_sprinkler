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

# Hauptpumpe (optional - wenn nicht gesetzt wird Zonen-Switch direkt verwendet)
CONF_MAIN_PUMP_SWITCH = "main_pump_switch"

# Durchflussmesser (optional - Template-Sensor der Gesamtdurchfluss summiert)
CONF_FLOW_SENSOR = "flow_sensor"
CONF_FLOW_PAUSE_LITERS = "flow_pause_liters"
DEFAULT_FLOW_PAUSE_LITERS = 200.0

# Manuell-Modus Timer-Toggle
CONF_MANUAL_USE_TIMER = "manual_use_timer"
DEFAULT_MANUAL_USE_TIMER = True

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

CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_TITLE = "notify_title"
DEFAULT_NOTIFY_TITLE = ""

# State-Konstanten
STATE_IDLE = "idle"
STATE_WATERING = "watering"
STATE_PAUSING = "pausing"
STATE_WIND_HOLD = "wind_hold"
STATE_WAITING_WATER = "waiting_water"  # wartet auf Brunnen-Erholung (Durchfluss-Pause)

# Attribute
ATTR_REMAINING_S = "remaining_seconds"
ATTR_CURRENT_BLOCK = "current_block"
ATTR_TOTAL_BLOCKS = "total_blocks"
ATTR_NEXT_START = "next_start"
ATTR_LAST_RUN = "last_run"
ATTR_NEXT_ZONE = "next_zone"
ATTR_PAUSE_MODE = "pause_mode"  # "time" oder "sensor"

# Konfigurations-Schlüssel (Einstellungen)
CONF_TARGET_MOISTURE = "target_moisture"
CONF_SECONDS_PER_PERCENT = "seconds_per_percent"
CONF_MIN_RUNTIME = "min_runtime"
CONF_MAX_RUNTIME = "max_runtime"
CONF_BLOCK_DURATION = "block_duration"
CONF_PAUSE_DURATION = "pause_duration"
CONF_WIND_SPEED_LIMIT = "wind_speed_limit"
CONF_WIND_GUST_LIMIT = "wind_gust_limit"
CONF_SOLAR_THRESHOLD = "solar_threshold"
CONF_EARLIEST_START = "earliest_start"
# Benachrichtigungs-Einstellungen
CONF_NOTIFY_ON_START = "notify_on_start"
CONF_NOTIFY_ON_FINISH = "notify_on_finish"
CONF_NOTIFY_ON_BLOCK_PAUSE = "notify_on_block_pause"
CONF_NOTIFY_ON_STOP = "notify_on_stop"
CONF_NOTIFY_ON_WIND = "notify_on_wind"
CONF_NOTIFY_ON_WATER_LEVEL = "notify_on_water_level"
CONF_NOTIFY_ON_NEXT_ZONE = "notify_on_next_zone"
CONF_NOTIFY_ON_NO_WATER_NEEDED = "notify_on_no_water_needed"

DEFAULT_NOTIFY_ON_START = True
DEFAULT_NOTIFY_ON_FINISH = True
DEFAULT_NOTIFY_ON_BLOCK_PAUSE = True
DEFAULT_NOTIFY_ON_STOP = True
DEFAULT_NOTIFY_ON_WIND = True
DEFAULT_NOTIFY_ON_WATER_LEVEL = True
DEFAULT_NOTIFY_ON_NEXT_ZONE = True
DEFAULT_NOTIFY_ON_NO_WATER_NEEDED = False

CONF_MIN_REMAINDER_BLOCK = "min_remainder_block"
DEFAULT_MIN_REMAINDER_BLOCK = 2.0

# Bewässerungsmodi
MODE_AUTO = "Automatik"
MODE_CHAIN = "Kette"
MODE_MANUAL = "Manuell"
CONF_MODE = "mode"
DEFAULT_MODE = "Automatik"

# Kette
CONF_CHAIN_POSITION = "chain_position"
DEFAULT_CHAIN_POSITION = 1

# Manuelle Laufzeit
CONF_MANUAL_DURATION = "manual_duration"
DEFAULT_MANUAL_DURATION = 20.0
