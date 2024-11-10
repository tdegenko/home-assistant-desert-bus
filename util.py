import math


class BusMath:
    # Math Largely from: https://loadingreadyrun.com/forum/viewtopic.php?t=10231
    @staticmethod
    def price_for_hour(hour: int, rate: float = 1.07) -> float:
        return round(rate ** (hour), 2)

    @staticmethod
    def dollars_to_hours(dollars: float, rate: float = 1.07) -> int:
        # NOTE: This is not reflexive with hours_to_dollats
        return math.floor(math.log((dollars * (rate - 1)) + 1) / math.log(rate))

    @staticmethod
    def hours_to_dollars(hours: int, rate: float = 1.07) -> float:
        return round((1 - (rate**hours)) / (1 - rate), 2)
