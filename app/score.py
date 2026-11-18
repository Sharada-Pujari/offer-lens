"""Turn the message itself into the number on the page.

The text model scores three classes at once. On a long notice those three
shares often sit near 40 percent even when the label is right, so two
different offers were showing 44 and 42. The offer score counts the facts
in the message. A role, pay, an eligibility line, rounds, cities, a last
date, and an official form each add a step. A service bond takes a step
off. The model still nudges the result, so the same facts in different
wording do not land on one identical number.
"""

from __future__ import annotations

import re

from app.decide import LABELS
from app.signals import EMAIL_RE, FREEMAIL

# Points for a fact a reader can see. The total is the scale, not a cap
# that every complete notice hits.
FACTS: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    ("role", 10, re.compile(r"\brole\b|job type|full-time|full time|\btrainee\b|\binternship\b", re.I)),
    ("pay", 12, re.compile(r"\b(?:ctc|stipend|salary|lpa|package|packege)\b|/month|per month", re.I)),
    ("amount", 6, re.compile(r"(?:₹|rs\.?|inr)\s?\d|\d+(?:\.\d+)?\s*lpa|\d[\d,]+\s*(?:/month|per month)", re.I)),
    ("eligibility", 10, re.compile(r"eligib|\bcgpa\b|backlogs?|%", re.I)),
    ("criteria_number", 4, re.compile(r"\d+(?:\.\d+)?\s*(?:%|cgpa)|\bcgpa\s*\d", re.I)),
    ("rounds", 10, re.compile(r"interview|technical round|online test|selection process|hr round", re.I)),
    ("second_round", 5, re.compile(r"technical.+hr|hr.+technical", re.I)),
    ("locations", 8, re.compile(r"\blocations?\b", re.I)),
    ("deadline", 6, re.compile(r"last date|apply by|deadline", re.I)),
    ("portal", 10, re.compile(r"superset|careers (?:page|portal)|placement (?:office|cell)|college email", re.I)),
    ("no_fee", 5, re.compile(r"no fees?|does not charge|do not pay|no payment|no deposit|without a (?:fee|payment)", re.I)),
)
CITY_RE = re.compile(
    r"\b(?:bangalore|bengaluru|chennai|mysore|mysuru|hyderabad|pune|mumbai|"
    r"vadodara|delhi|noida|gurgaon|gurugram|kolkata|ahmedabad)\b",
    re.I,
)
POINT_SCALE = sum(points for _name, points, _pattern in FACTS) + 4 + 5


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def evidence_points(text: str) -> int:
    if not text:
        return 0
    total = 0
    for _name, points, pattern in FACTS:
        if pattern.search(text):
            total += points
    cities = {match.group(0).lower() for match in CITY_RE.finditer(text)}
    if len(cities) >= 3:
        total += 4
    for match in EMAIL_RE.finditer(text):
        domain = match.group(0).split("@", 1)[1].lower()
        if domain not in FREEMAIL:
            total += 5
            break
    return total


def offer_score(
    label: str,
    probabilities: dict[str, float],
    risks: list[dict],
    supports: list[dict],
    text: str = "",
) -> tuple[float, dict[str, float]]:
    if label not in LABELS:
        raise ValueError(f"Unknown label: {label}")

    high = [item for item in risks if item.get("severity") == "high"]
    medium = [item for item in risks if item.get("severity") == "medium" and item.get("id") != "service_bond"]
    bond = any(item.get("id") == "service_bond" for item in risks)
    coverage = evidence_points(text) / POINT_SCALE
    # Quoted support lines still count when the wording is too short for a fact regex.
    if supports and coverage < 0.15:
        coverage = min(0.15, 0.04 * len(supports))
    model = float(probabilities.get(label, 0.0))
    nudge = 0.08 * (model - 0.5)

    if label == "risky":
        shown = 0.70 + 0.06 * len(high) + 0.03 * len(medium) + nudge
        shown = _clip(shown, 0.68, 0.97)
    elif label == "unclear":
        shown = 0.32 + 0.28 * coverage + nudge
        shown = _clip(shown, 0.28, 0.58)
    else:
        shown = 0.56 + 0.38 * coverage + nudge
        if bond:
            shown -= 0.08
        shown -= 0.03 * len(medium)
        shown = _clip(shown, 0.55, 0.96)

    shown = round(shown, 3)
    return shown, _shares(label, shown, probabilities)


def _shares(label: str, shown: float, probabilities: dict[str, float]) -> dict[str, float]:
    others = [name for name in LABELS if name != label]
    rest = 1.0 - shown
    weights = [max(float(probabilities.get(name, 0.0)), 0.02) for name in others]
    total = sum(weights)
    raw = {label: shown}
    for name, weight in zip(others, weights):
        raw[name] = rest * weight / total
    rounded = {name: round(raw[name], 3) for name in LABELS}
    drift = round(1.0 - sum(rounded.values()), 3)
    adjust = min(others, key=lambda name: rounded[name])
    rounded[adjust] = round(rounded[adjust] + drift, 3)
    return rounded
