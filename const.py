"""Constants for the Desert Bus integration."""

DOMAIN = "desertbus"
SIGNAL_EVENTS_CHANGED = f"{DOMAIN}_events_changed"

CHECK_URL_BASE = "https://vst.ninja"

OMEGA_CHECK_URL = f"{CHECK_URL_BASE}/Resources/isitomegashift.html"

STATS_URL_TEMPLATE = f"{CHECK_URL_BASE}/DB{{year}}/data/DB{{year}}_stats.json"

DB_YEAR_OFFSET = 2006

class SHIFTS:
    DAWN = "Dawn Guard"
    ALPHA = "Alpha Flight"
    NIGHT = "Night Watch"
    ZETA = "Zeta Shift"
    OMEGA = "Omega Shift"
