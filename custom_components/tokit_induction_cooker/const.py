"""Constants for the TOKIT induction cooker (chunmi.ihcooker.cbhw).

Property and action numbers come from the cooker's published MIoT spec:
urn:miot-spec-v2:device:induction-cooker:0000A033:chunmi-cbhw:1
"""
from datetime import timedelta

DOMAIN = "tokit_induction_cooker"

# Models this has been seen working on. Every number below comes from this one model's spec,
# and the same numbers sent to a different hob could mean something else, so setup refuses
# anything not listed here.
SUPPORTED_MODELS = {"chunmi.ihcooker.cbhw"}

# How often to read the cooker. A real one answered 217 reads in a row at 10 seconds apart.
IDLE_INTERVAL = timedelta(seconds=10)
ACTIVE_INTERVAL = timedelta(seconds=5)
# A cooker with its internet access blocked dropped off the Wi-Fi and rejoined about every 15
# minutes, missing one read each time. A missed read keeps the last reading for this long before
# the entities show as unavailable.
KEEP_LAST_READING = timedelta(seconds=30)
# After a command the cooker is read at once, and once more this many seconds later in case
# it hadn't caught up. A real one does: each change showed on the read 2 seconds later, not the first.
FOLLOW_UP_SECONDS = 2

# The beeper setting, buzzer-mark in the spec. One of the three properties it lets you write.
PROP_MUTED = (3, 25)

# key: (siid, piid). Twelve properties, the most one request has been seen to read.
PROPERTIES = {
    "status": (2, 1),
    "fault": (2, 2),
    "time_remaining": (2, 5),
    "cooking_time": (2, 6),
    "phase": (3, 2),
    "work_status": (3, 3),
    "temperature": (3, 7),
    "target_temperature": (3, 8),
    "power_level": (3, 9),
    "recipe_type": (3, 15),
    "menu": (3, 1),
    "muted": PROP_MUTED,
}

STATUS = {0: "idle", 1: "cooking", 2: "timing", 3: "scheduled", 4: "paused", 5: "off"}
STATUS_HEATING = {1, 2}
# Cooking or paused: the states where power and temperature can be changed, and the ones read faster.
STATUS_ADJUSTABLE = {1, 2, 4}

FAULT = {
    0: "none",
    2: "no_pan",
    3: "high_voltage",
    4: "low_voltage",
    5: "surface_overheat",
    7: "igbt_overheat",
    8: "igbt_sensor",
    10: "surface_sensor",
    11: "communication",
    12: "coil_open",
}

WORK_STATUS = {
    1: "idle",
    2: "cooking",
    4: "scheduled",
    8: "error",
    9: "idle_timer",
    10: "cooking_timer",
    11: "off",
    12: "paused",
    14: "charging",
    18: "stopping",
    19: "timer_paused",
}

# The status shown is worked out from 3.3 work-status where it has an equivalent, and from 2.1
# status otherwise. A real cooker with its internet access blocked kept 2.1 at 5 (off) through a
# whole cook, a pause, a resume and a stop, while 3.3 showed each one: 2, 12, 2, then 1. 1, 2, 11
# and 12 have been seen on a real cooker. 4, 10 and 19 are mapped from the spec's names for them.
WORK_STATUS_TO_STATUS = {1: 0, 2: 1, 4: 3, 10: 2, 11: 5, 12: 4, 19: 4}

RECIPE_TYPE = {0: "preset", 1: "single_power", 2: "multi_power", 3: "single_temperature", 4: "recipe"}

# What each number selects, read back from a real cooker. The published spec labels 3 to 5
# as simmer, stir fry and deep fry, which is wrong for this model.
COOK_MODES = {"hotpot": 1, "steam_boil": 2, "stir_fry": 3, "fry": 4, "soup": 5}

# Actions: (siid, aiid)
# Wakes the cooker and selects a mode. It does not heat: the cooker then asks for a press
# on its own start button. in: cook-mode (2.8)
ACTION_START_COOK = (2, 1)
ACTION_CANCEL = (2, 2)
ACTION_PAUSE = (2, 3)
ACTION_RESUME = (3, 3)  # in: information (3.20), user-id (3.19)
ACTION_SET_POWER = (3, 13)  # in: fire-gears (3.9), information, user-id
ACTION_SET_TEMPERATURE = (3, 14)  # in: target-temperature (3.8), information, user-id

PIID_COOK_MODE = 8
PIID_TARGET_TEMPERATURE = 8
PIID_POWER_LEVEL = 9
PIID_USER_ID = 19
PIID_INFORMATION = 20

# Read this seldom while the cooker doesn't answer, as when it's switched off at the wall, so an appliance that is
# often unplugged doesn't keep a worker thread waiting on timeouts every few seconds.
OFFLINE_INTERVAL = timedelta(seconds=30)
# Setup keeps these from the cooker's miIO.info in the config entry, so it can set up while the cooker is off.
CONF_INFO = "info"
INFO_REMEMBERED = ("mac", "model", "fw_ver", "mcu_fw_ver", "hw_ver")
