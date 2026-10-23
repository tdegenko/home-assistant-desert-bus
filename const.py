"""Constants for the Desert Bus integration."""

import datetime
import enum

DOMAIN = "desertbus"
SIGNAL_EVENTS_CHANGED = f"{DOMAIN}_events_changed"

CHECK_URL_BASE = "https://vst.ninja"
SCRAPE_URL_BASE = "https://desertbus.org"

OMEGA_CHECK_URL = f"{CHECK_URL_BASE}/Resources/isitomegashift.html"

STATS_URL_TEMPLATE = f"{CHECK_URL_BASE}/DB{{year}}/data/DB{{year}}_stats.json"
SCRAPE_URL_TEMPLATE = f"{SCRAPE_URL_BASE}/{{year}}/"

DB_YEAR_OFFSET = 2006

RATE_LIMITS: dict = {
    "STATS": {
        "PRE_RUN": datetime.timedelta(minutes=30),
        "DURING_RUN": datetime.timedelta(minutes=15),
        "POST_RUN": datetime.timedelta(hours=6),
    },
    "OMEGA_SHIFT": datetime.timedelta(minutes=10),
}

BUS_TIMEZONE = datetime.timezone(datetime.timedelta(hours=-7))


class SHIFTS(enum.Enum):
    """Define shift names."""

    DAWN = "Dawn Guard"
    ALPHA = "Alpha Flight"
    NIGHT = "Night Watch"
    ZETA = "Zeta Shift"
    OMEGA = "Omega Shift"

    @staticmethod
    def from_time(time=datetime.time) -> "SHIFTS":
        """Get typical shift for a give time (time in bus timezone)."""
        if datetime.time(0) <= time < datetime.time(6):
            return SHIFTS.ZETA
        if datetime.time(6) <= time < datetime.time(12):
            return SHIFTS.DAWN
        if datetime.time(12) <= time < datetime.time(18):
            return SHIFTS.ALPHA
        return SHIFTS.NIGHT

    @property
    def colors(self) -> dict[str, list[int]]:
        """ """
        _shift_colors = {
            SHIFTS.DAWN: {
                "primary": [239, 130, 34],
                "secondary": [192, 106, 41],
                "tertiary": [236, 227, 58],
            },
            SHIFTS.ALPHA: {
                "primary": [188, 37, 41],
                "secondary": [116, 18, 20],
                "tertiary": [188, 37, 41],
            },
            SHIFTS.NIGHT: {
                "primary": [9, 114, 186],
                "secondary": [36, 34, 98],
                "tertiary": [34, 171, 226],
            },
            SHIFTS.ZETA: {
                "primary": [94, 55, 137],
                "secondary": [145, 100, 171],
                "tertiary": [94, 55, 137],
            },
            SHIFTS.OMEGA: {
                "primary": [117, 204, 214],
                "secondary": [229, 160, 43],
                "tertiary": [115, 116, 116],
            },
        }
        return _shift_colors[self]
