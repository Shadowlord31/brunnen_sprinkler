DOMAIN = "brunnen_bewasserung"

# Entry-Typen
ENTRY_TYPE_GARTEN = "garten"
ENTRY_TYPE_ZONE = "zone"
ENTRY_TYPE_MANUELL = "manuell"
CONF_ENTRY_TYPE = "entry_type"

# === GARTEN ===
CONF_GARTEN_NAME = "garten_name"
CONF_SOLAR_SENSOR = "solar_sensor"
CONF_WIND_SPEED_SENSOR = "wind_speed_sensor"
CONF_WIND_GUST_SENSOR = "wind_gust_sensor"
CONF_MAIN_PUMP_SWITCH = "main_pump_switch"
CONF_FLOW_SENSOR = "flow_sensor"
CONF_FLOW_PAUSE_LITERS = "flow_pause_liters"
CONF_FLOW_IDLE_TIMEOUT = "flow_idle_timeout"   # Minuten bis Brunnen-Reset
CONF_WIND_SPEED_LIMIT = "wind_speed_limit"
CONF_WIND_GUST_LIMIT = "wind_gust_limit"
CONF_SOLAR_THRESHOLD = "solar_threshold"
CONF_EARLIEST_START = "earliest_start"
CONF_BLOCK_DURATION = "block_duration"
CONF_PAUSE_DURATION = "pause_duration"
CONF_MIN_RUNTIME = "min_runtime"
CONF_MAX_RUNTIME = "max_runtime"
CONF_GIESS_ENABLED = "giess_assistent_enabled"
CONF_GIESS_SENSOR = "giess_assistent_sensor"

DEFAULT_FLOW_PAUSE_LITERS = 200.0
DEFAULT_FLOW_IDLE_TIMEOUT = 15.0
CONF_AUTO_PUMP_OFF = "auto_pump_off"
DEFAULT_AUTO_PUMP_OFF = True
DEFAULT_WIND_SPEED_LIMIT = 15.0
DEFAULT_WIND_GUST_LIMIT = 25.0
DEFAULT_SOLAR_THRESHOLD = 400.0
DEFAULT_EARLIEST_START = "17:30"
DEFAULT_BLOCK_DURATION = 15.0
DEFAULT_PAUSE_DURATION = 15.0
DEFAULT_MIN_RUNTIME = 5.0
DEFAULT_MAX_RUNTIME = 100.0

# === ZONE ===
CONF_PARENT_ENTRY_ID = "parent_entry_id"
CONF_INSTANCE_NAME = "instance_name"
CONF_PUMP_SWITCH = "pump_switch"
CONF_MOISTURE_SENSOR = "moisture_sensor"
CONF_TARGET_MOISTURE = "target_moisture"
CONF_SECONDS_PER_PERCENT = "seconds_per_percent"
CONF_FIXED_RUNTIME = "fixed_runtime"
CONF_AUTO_ENABLED = "auto_enabled"
CONF_ZONE_START_TIME = "zone_start_time"
DEFAULT_ZONE_START_TIME = "17:30"
CONF_MIN_REMAINDER_BLOCK = "min_remainder_block"
CONF_IGNORE_WIND = "ignore_wind"
DEFAULT_IGNORE_WIND = False
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_TITLE = "notify_title"

DEFAULT_TARGET_MOISTURE = 45.0
DEFAULT_SECONDS_PER_PERCENT = 395.0
DEFAULT_FIXED_RUNTIME = 20.0
DEFAULT_AUTO_ENABLED = True
DEFAULT_MIN_REMAINDER_BLOCK = 2.0
DEFAULT_NOTIFY_TITLE = ""

# States
STATE_IDLE = "idle"
STATE_WATERING = "watering"
STATE_PAUSING = "pausing"
STATE_WIND_HOLD = "wind_hold"
STATE_WAITING_WATER = "waiting_water"
STATE_MANUAL = "manual"
STATE_WAITING_ZONE = "waiting_zone"  # wartet bis andere Zone fertig
STATE_MANUELL_OPEN = "manuell_open"   # Manuell-Zone: Ventil offen
STATE_MANUELL_PAUSE = "manuell_pause"  # Manuell-Zone: Brunnenpause
STATE_MANUAL_HOLD = "manual_hold"  # Automatik-Zone: manuell pausiert (eigenes Ventil zu, Hauptpumpe laeuft weiter)

# Attribute
ATTR_REMAINING_S = "remaining_seconds"
ATTR_CURRENT_BLOCK = "current_block"
ATTR_TOTAL_BLOCKS = "total_blocks"
ATTR_NEXT_START = "next_start"
ATTR_LAST_RUN = "last_run"

# Benachrichtigungen
CONF_NOTIFY_ON_START = "notify_on_start"
CONF_NOTIFY_ON_FINISH = "notify_on_finish"
CONF_NOTIFY_ON_BLOCK_PAUSE = "notify_on_block_pause"
CONF_NOTIFY_ON_STOP = "notify_on_stop"
CONF_NOTIFY_ON_WIND = "notify_on_wind"
CONF_NOTIFY_ON_NO_WATER_NEEDED = "notify_on_no_water_needed"

DEFAULT_NOTIFY_ON_START = True
DEFAULT_NOTIFY_ON_FINISH = True
DEFAULT_NOTIFY_ON_BLOCK_PAUSE = True
DEFAULT_NOTIFY_ON_STOP = True
DEFAULT_NOTIFY_ON_WIND = True
DEFAULT_NOTIFY_ON_NO_WATER_NEEDED = False
