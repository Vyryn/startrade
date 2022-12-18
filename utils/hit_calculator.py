import math

bonuses = {"vet": 10, "ace": 15, "hon": 20, "evad": 20, "jam": 20}


def f_length(length: float) -> float:
    return 20 * math.log(length / 10 + 1)


def f_speed_over_turn_rate(speed: float, turn_rate: float) -> float:
    return 15 / (math.log(speed + 0.0001) / turn_rate) + 3


def f_dist_over_accuracy(dist: float, accuracy: float) -> float:
    return 100 * math.pow(2, ((-1 * dist / accuracy) / 2))


def hit_chance(
    distance: float,
    effective_range: float,
    ship_length: float,
    weapon_accuracy: float,
    weapon_turn_rate: float,
    ship_speed: float,
    bonus: float = 0,
) -> float:
    """Calculates the % chance a shot under the given circumstances hits.
        distance: in km
        ship_length: in meters
        weapon_accuracy: 1-100
        weapon_turn_rate: 1-100
        ship_speed: in MGLT

        bonus: A flat % subtracted from the hit chance after all other modifiers are applied

    New formula:
        max intended resonable range for any combat = 200km
    Longer ship -> more likely to hit
    Higher turn rate -> less negative impact of ship speed on hit chance when close

    Faster ship -> less likely to hit
    More accurate weapon -> more likely to hit
    Each weapon has:
        turn_rate
        accuracy
        damage
        fire_rate

    Each ship has:
        length
        speed

    Encounter has:
        distance

    Turbolaser vs Star Destroyer @ 100km:
        weapon_turn_rate = 30
        weapon_accuracy = 60
        distance = 100
        length = 2000
        speed = 60

    hit rate = f(length)*g(turn_rate)*h(accuracy)*k(distance, turn_rate)*m(speed)
    """
    res = (
        math.pow(10, -4)
        * 0.6
        * f_length(ship_length)
        * f_speed_over_turn_rate(ship_speed, weapon_turn_rate)
        * f_dist_over_accuracy(distance, weapon_accuracy)
    )
    res += bonus
    res = min(res, 99)
    res = max(res, 0.1)
    return res
