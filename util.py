import math

from .const import DB_YEAR_OFFSET


class BusMath:
    # Math Largely from: https://loadingreadyrun.com/forum/viewtopic.php?t=10231
    @staticmethod
    def price_for_hour(hour: int, rate: float = 1.07) -> float:
        """Return the price for a given hour."""
        return round(rate ** (hour), 2)

    @staticmethod
    def dollars_to_hours(dollars: float, rate: float = 1.07) -> int:
        """Return how many hours have been paid for by a given number of dollars."""
        # NOTE: This is not reflexive with hours_to_dollars
        return math.floor(math.log((dollars * (rate - 1)) + 1) / math.log(rate))

    @staticmethod
    def hours_to_dollars(hours: int, rate: float = 1.07) -> float:
        """"Return the minumum number of dollars needed to pay for a given number of hours."""
        return round((1 - (rate**hours)) / (1 - rate), 2)

    def get_db_count(year: int) -> int:
        """Return what year of DB (prime) a given year is."""
        return year - DB_YEAR_OFFSET
