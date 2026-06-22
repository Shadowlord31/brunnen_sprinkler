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
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_TITLE = "notify_title"
DEFAULT_NOTIFY_TITLE = ""

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