from __future__ import annotations

import random


FORTUNE_BASELINE = 12.0


def clamp_probability(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(min(float(value or 0.0), float(maximum)), float(minimum))


def adjust_probability_percent(
    base_percent: float,
    actor_fortune: float | int | None = None,
    opponent_fortune: float | int | None = None,
    actor_weight: float = 0.4,
    opponent_weight: float = 0.25,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    adjusted = float(base_percent or 0.0)
    if actor_fortune is not None:
        adjusted += (float(actor_fortune) - FORTUNE_BASELINE) * float(actor_weight)
    if opponent_fortune is not None:
        adjusted -= (float(opponent_fortune) - FORTUNE_BASELINE) * float(opponent_weight)
    return clamp_probability(adjusted, minimum=minimum, maximum=maximum)


def adjust_probability_rate(
    base_rate: float,
    actor_fortune: float | int | None = None,
    opponent_fortune: float | int | None = None,
    actor_weight: float = 0.4,
    opponent_weight: float = 0.25,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return adjust_probability_percent(
        float(base_rate or 0.0) * 100.0,
        actor_fortune=actor_fortune,
        opponent_fortune=opponent_fortune,
        actor_weight=actor_weight,
        opponent_weight=opponent_weight,
        minimum=float(minimum) * 100.0,
        maximum=float(maximum) * 100.0,
    ) / 100.0


def roll_probability_percent(
    base_percent: float,
    actor_fortune: float | int | None = None,
    opponent_fortune: float | int | None = None,
    actor_weight: float = 0.4,
    opponent_weight: float = 0.25,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> dict[str, float | int | bool]:
    chance = adjust_probability_percent(
        base_percent,
        actor_fortune=actor_fortune,
        opponent_fortune=opponent_fortune,
        actor_weight=actor_weight,
        opponent_weight=opponent_weight,
        minimum=minimum,
        maximum=maximum,
    )
    roll = random.randint(1, 100)
    return {
        "success": roll <= chance,
        "roll": roll,
        "chance": round(chance, 2),
        "base_chance": round(float(base_percent or 0.0), 2),
    }
