"""
engine/math.py — Pure computational logic for GridDrop.

No Discord imports. No Pillow imports. Fully unit-testable in isolation.

Key design decisions:
  - Distance is always normalised to [0.0, 1.0] before scoring, so the
    scoring curve is identical regardless of World Pack scale.
  - The maximum possible distance on any square grid is the diagonal
    (√2 × grid_size), which we use as the normalisation denominator.
  - Score decay uses a tunable exponential curve. Default k=5 gives:
      distance = 0%  → 5000 pts  (perfect)
      distance = 10% → ~3033 pts
      distance = 25% → ~1353 pts
      distance = 50% →  ~369 pts
      distance = 100% →   0 pts
"""

from __future__ import annotations
import math
import random
from typing import Optional

from ..models.coordinates import GridPoint, MacroSector, MicroCell


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_SIZE: int = 100   # effective resolution of the 2-tier 10×10 grid
MAX_DISTANCE: float = math.sqrt(2) * GRID_SIZE   # ≈ 141.42


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def cartesian_distance(a: GridPoint, b: GridPoint) -> float:
    """
    Euclidean distance between two GridPoints in grid-unit space.

    Returns a value in [0, MAX_DISTANCE].
    """
    return math.hypot(b.x - a.x, b.y - a.y)


def normalize_distance(
    distance: float,
    max_distance: float = MAX_DISTANCE,
) -> float:
    """
    Map a raw grid distance to [0.0, 1.0].

    0.0 = perfect hit, 1.0 = opposite corner of the map.
    Clamps to [0, 1] so World Pack custom scales never produce NaN scores.
    """
    if max_distance <= 0:
        return 0.0
    return max(0.0, min(1.0, distance / max_distance))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def calculate_score(
    distance: float,
    *,
    max_score: int = 5000,
    k: float = 5.0,
    perfect_radius: float = 0.5,
) -> int:
    """
    Exponential-decay score from a raw grid distance.

    Parameters
    ----------
    distance      : raw Euclidean distance in grid-unit space
    max_score     : points awarded for a perfect guess
    k             : decay steepness (higher k → faster drop-off)
    perfect_radius: grid-unit radius within which full points are awarded

    Returns an integer in [0, max_score].
    """
    if distance <= perfect_radius:
        return max_score

    normalised = normalize_distance(distance)
    score = max_score * math.exp(-k * normalised)
    return max(0, round(score))


def score_guess(
    target: GridPoint,
    guess: GridPoint,
    *,
    max_score: int = 5000,
    k: float = 5.0,
    map_max_distance: Optional[float] = None,
) -> tuple[int, float]:
    """
    Score a single guess against the target.

    Returns (score, raw_distance). Callers typically want both:
      - score  → write to Config / leaderboard
      - distance → display in the reveal embed ("you were X units away")

    Parameters
    ----------
    map_max_distance : override if the World Pack defines a custom max diagonal
                       (e.g. a non-square map). Defaults to GRID_SIZE diagonal.
    """
    dist = cartesian_distance(target, guess)
    effective_max = map_max_distance or MAX_DISTANCE
    normalised = normalize_distance(dist, effective_max)
    score = max_score * math.exp(-k * normalised)
    score = max(0, round(score))
    if dist <= 0.5:
        score = max_score
    return (score, dist)


# ---------------------------------------------------------------------------
# Target generation
# ---------------------------------------------------------------------------

def random_target(grid_size: int = GRID_SIZE) -> GridPoint:
    """
    Pick a uniformly random target anywhere on the grid.

    Uses a continuous uniform distribution so the target is not
    snapped to the centre of a sector—it can land anywhere in [0, grid_size).
    """
    x = random.uniform(0.0, float(grid_size - 1))
    y = random.uniform(0.0, float(grid_size - 1))
    return GridPoint(x=x, y=y)


def target_from_tiers(macro: MacroSector, micro: MicroCell) -> GridPoint:
    """Construct a GridPoint from explicit tier selections (used in testing)."""
    return GridPoint.from_tiers(macro, micro)


# ---------------------------------------------------------------------------
# Scoring utilities (leaderboard / stats helpers)
# ---------------------------------------------------------------------------

def percentage_accuracy(distance: float, max_distance: float = MAX_DISTANCE) -> float:
    """
    Express accuracy as a 0-100% value (higher = closer).
    Suitable for the 'average_distance' stat in RedBot Config.
    """
    return max(0.0, (1.0 - normalize_distance(distance, max_distance)) * 100.0)


def rank_guesses(
    guesses: list[tuple[int, GridPoint]],
    target: GridPoint,
    *,
    max_score: int = 5000,
    k: float = 5.0,
) -> list[dict]:
    """
    Score and rank a list of (user_id, guess_point) pairs.

    Returns a list of result dicts sorted from highest to lowest score:
        [{"user_id": int, "score": int, "distance": float, "rank": int}, ...]

    Ties are broken by distance (closer wins); if still tied, by insertion order.
    """
    results = []
    for user_id, guess in guesses:
        score, dist = score_guess(target, guess, max_score=max_score, k=k)
        results.append({
            "user_id": user_id,
            "score": score,
            "distance": dist,
        })

    results.sort(key=lambda r: (-r["score"], r["distance"]))

    for rank, result in enumerate(results, start=1):
        result["rank"] = rank

    return results
