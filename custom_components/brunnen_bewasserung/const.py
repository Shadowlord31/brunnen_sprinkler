DOMAIN = "brunnen_bewasserung"

# Entry-Typen
ENTRY_TYPE_GARTEN = "garten"
ENTRY_TYPE_ZONE = "zone"
CONF_ENTRY_TYPE = "entry_type"

# Garten-Konfiguration
CONF_GARTEN_NAME = "garten_name"
CONF_SOLAR_SENSOR = "solar_sensor"
CONF_WIND_SPEED_SENSOR = "wind_speed_sensor"
CONF_WIND_GUST_SENSOR = "wind_gust_sensor"
CONF_MAIN_PUMP_SWITCH = "main_pump_switch"
CONF_FLOW_SENSOR = "flow_sensor"
CONF_FLOW_PAUSE_LITERS = "flow_pause_liters"
CONF_WIND_SPEED_LIMIT = "wind_speed_limit"
CONF_WIND_GUST_LIMIT = "wind_gust_limit"
CONF_SOLAR_THRESHOLD = "solar_threshold"
CONF_EARLIEST_START = "earliest_start"

DEFAULT_FLOW_PAUSE_LITERS = 200.0
DEFAULT_WIND_SPEED_LIMIT = 15.0
DEFAULT_WIND_GUST_LIMIT = 25.0
DEFAULT_SOLAR_THRESHOLD = 400.0
DEFAULT_EARLIEST_START = "17:30"

# Zonen-Konfiguration
CONF_PARENT_ENTRY_ID = "parent_entry_id"
CONF_INSTANCE_NAME = "instance_name"
CONF_PUMP_SWITCH = "pump_switch"
CONF_MOISTURE_SENSOR = "moisture_sensor"       # optional
CONF_TARGET_MOISTURE = "target_moisture"
CONF_SECONDS_PER_PERCENT = "seconds_per_percent"
CONF_MIN_RUNTIME = "min_runtime"
CONF_MAX_RUNTIME = "max_runtime"
CONF_FIXED_RUNTIME = "fixed_runtime"           # wenn kein Bodensensor
CONF_BLOCK_DURATION = "block_duration"
CONF_PAUSE_DURATION = "pause_duration"
CONF_MIN_REMAINDER_BLOCK = "min_remainder_block"
CONF_MODE = "mode"
CONF_CHAIN_POSITION = "chain_position"
CONF_MANUAL_DURATION = "manual_duration"
CONF_MANUAL_USE_TIMER = "manual_use_timer"
CONF_GIESS_ENABLED = "giess_assistent_enabled"
CONF_GIESS_SENSOR = "giess_assistent_sensor"
CONF_NEXT_ZONE_ENTRY_ID = "next_zone_entry_id"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_TITLE = "notify_title"

DEFAULT_TARGET_MOISTURE = 45.0
DEFAULT_SECONDS_PER_PERCENT = 395.0
DEFAULT_MIN_RUNTIME = 5.0
DEFAULT_MAX_RUNTIME = 100.0
DEFAULT_FIXED_RUNTIME = 20.0
DEFAULT_BLOCK_DURATION = 15.0
DEFAULT_PAUSE_DURATION = 15.0
DEFAULT_MIN_REMAINDER_BLOCK = 2.0
DEFAULT_MODE = "Automatik"
DEFAULT_CHAIN_POSITION = 1
DEFAULT_MANUAL_DURATION = 20.0
DEFAULT_MANUAL_USE_TIMER = True
DEFAULT_NOTIFY_TITLE = ""

# Bewässerungsmodi
MODE_AUTO = "Automatik"
MODE_CHAIN = "Kette"
MODE_MANUAL = "Manuell"

# State-Konstanten
STATE_IDLE = "idle"
STATE_WATERING = "watering"
STATE_PAUSING = "pausing"
STATE_WIND_HOLD = "wind_hold"
STATE_WAITING_WATER = "waiting_water"

# Attribute
ATTR_REMAINING_S = "remaining_seconds"
ATTR_CURRENT_BLOCK = "current_block"
ATTR_TOTAL_BLOCKS = "total_blocks"
ATTR_NEXT_START = "next_start"
ATTR_LAST_RUN = "last_run"
ATTR_NEXT_ZONE = "next_zone"

# Benachrichtigungen
CONF_NOTIFY_ON_START = "notify_on_start"
CONF_NOTIFY_ON_FINISH = "notify_on_finish"
CONF_NOTIFY_ON_BLOCK_PAUSE = "notify_on_block_pause"
CONF_NOTIFY_ON_STOP = "notify_on_stop"
CONF_NOTIFY_ON_WIND = "notify_on_wind"
CONF_NOTIFY_ON_NEXT_ZONE = "notify_on_next_zone"
CONF_NOTIFY_ON_NO_WATER_NEEDED = "notify_on_no_water_needed"

DEFAULT_NOTIFY_ON_START = True
DEFAULT_NOTIFY_ON_FINISH = True
DEFAULT_NOTIFY_ON_BLOCK_PAUSE = True
DEFAULT_NOTIFY_ON_STOP = True
DEFAULT_NOTIFY_ON_WIND = True
DEFAULT_NOTIFY_ON_NEXT_ZONE = True
DEFAULT_NOTIFY_ON_NO_WATER_NEEDED = False
