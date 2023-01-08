import math
import random
from collections import Counter

bonuses = {"vet": 10, "ace": 15, "hon": 20, "evad": 20, "jam": 20}


def f_length(length: float) -> float:
    return 20 * math.log(length / 10 + 1)


def f_speed_over_turn_rate(speed: float, turn_rate: float) -> float:
    return 15 / (math.log(speed + 0.0001) / turn_rate) + 3


def f_dist_over_accuracy(dist: float, accuracy: float) -> float:
    return 100 * math.pow(2, ((-1 * dist / accuracy) / 2))


def hit_chance(
    distance: float,
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
    res -= bonus
    res = min(res, 99)
    res = max(res, 0.01)
    return res


def hit_determine(
    distance: float,
    ship_length: float,
    weapon_accuracy: float,
    weapon_turn_rate: float,
    ship_speed: float,
    bonus: float = 0,
) -> bool:
    required_roll: float = hit_chance(
        distance,
        ship_length,
        weapon_accuracy,
        weapon_turn_rate,
        ship_speed,
        bonus=bonus,
    )
    roll: float = random.random() * 100
    if roll < required_roll:
        return True
    return False


def attenuate(damage: float, attenuation: float, dist: float) -> float:
    """Calculates the attenuated damage of a ship at a given distance."""
    if attenuation <= 0:
        return damage
    return damage * pow(2, (-1 / attenuation) * dist)


def damage_determine(
    hull: float,
    shields: float,
    weap_damage_shields: float,
    weap_damage_hull: float,
    pierce: float,
    attenuation: float,
    dist: float,
    do_attenuation: bool = False,
) -> (float, float):
    """Does damage with the provided weapon stats to the target hull and shields in absolute values *not* %s."""
    if do_attenuation:
        weap_damage_hull = attenuate(weap_damage_hull, attenuation, dist)
        weap_damage_shields = attenuate(weap_damage_shields, attenuation, dist)
    potential_shield_dmg = weap_damage_shields * (1 - pierce)
    if shields >= potential_shield_dmg:
        new_shields = shields - potential_shield_dmg
        hull_dmg = weap_damage_hull * pierce
        new_hull = hull - hull_dmg
        return max(new_hull, 0), new_shields
    elif shields == 0 or potential_shield_dmg <= 0:
        new_hull = hull - weap_damage_hull
        return max(new_hull, 0), 0
    fraction_done_to_shields = shields / potential_shield_dmg
    hull_damage = weap_damage_hull * (1 - fraction_done_to_shields)
    new_hull = hull - hull_damage
    return max(new_hull, 0), 0


def val_to_perc(value, max_) -> int:
    """Converts a value as a portion of max to a percentage"""
    if max_ <= 0:
        return 0
    return round(value / max_ * 100)


def perc_to_val(perc, max_):
    """Converts a percentage of max to a value"""
    return perc / 100.0 * max_


def calc_dmg(
    i_hull: float,
    i_shield: float,
    n_weaps: int,
    dist: float,
    bonus: int,
    ship_info: dict,
    weap_info: dict,
    do_attenuation: bool = False,
) -> (float, float):
    """Determines whether a weapon hits and if so calculates damage. Returns the new hull and shields."""
    # Look up values
    weap_damage_shields = weap_info["shield_dmg"]
    weap_damage_hull = weap_info["hull_dmg"]
    weap_rate = int(weap_info["rate"])
    pierce = weap_info["pierce"]
    weapon_accuracy = weap_info["accuracy"]
    attenuation = weap_info["attenuation"]
    weapon_turn_rate = weap_info["turn_speed"]

    ship_length = ship_info["len"]
    ship_speed = ship_info["speed"]
    max_hull = ship_info["hull"]
    max_shield = ship_info["shield"]
    # Values need to be in absolutes for damage_determine
    hull = perc_to_val(i_hull, max_hull)
    shield = perc_to_val(i_shield, max_shield)
    num_hits = 0
    # For each weapon, determine if it hits. If so, subtract the damage dealt by it.
    for _i in range(n_weaps):
        for _j in range(weap_rate):
            weap_hits = hit_determine(
                dist,
                ship_length,
                weapon_accuracy,
                weapon_turn_rate,
                ship_speed,
                bonus=bonus,
            )
            if not weap_hits:
                continue
            num_hits += 1
            (hull, shield) = damage_determine(
                hull,
                shield,
                weap_damage_shields,
                weap_damage_hull,
                pierce,
                attenuation,
                dist,
                do_attenuation=do_attenuation,
            )

    hit_perc = val_to_perc(num_hits, n_weaps * weap_rate)
    num_shots = n_weaps * weap_rate

    return (
        val_to_perc(hull, max_hull),
        val_to_perc(shield, max_shield),
        hit_perc,
        num_shots,
    )


def calc_dmg_multi(
    ships, n_weaps, dist, bonus, weap_info, do_attenuation: bool = False
):
    """Randomly scatters damage between a bunch of different ships of the same type.
    Returns a list of hull and shields and amounts."""
    total_hits = 0
    total_shots = 0

    for _ in range(n_weaps):
        selected_ship = random.randrange(len(ships))
        i_hull, i_shield, ship_info = ships[selected_ship]
        new_hull, new_shields, hit_perc, num_shots = calc_dmg(
            i_hull,
            i_shield,
            1,
            dist,
            bonus,
            ship_info,
            weap_info,
            do_attenuation=do_attenuation,
        )
        ships[selected_ship] = (new_hull, new_shields, ship_info)
        total_hits += round(hit_perc / 100 * num_shots)
        total_shots += num_shots
    final_hit_perc = val_to_perc(total_hits, total_shots)
    new_ships = Counter([(hull, shields) for hull, shields, _ in ships])
    return new_ships, final_hit_perc, total_shots
