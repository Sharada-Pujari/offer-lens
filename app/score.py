"""Turn a label and the quoted lines into the number on the page.

The text model scores three classes at once. On a long official notice it
often peaks near 0.4 even when credible is the winner, because ordinary
words are shared. The page should move with the lines a student can see:
a named role, pay, eligibility, rounds, locations, a last date, and an
official form raise the score. A service bond steps it down. A fee or an
identity request stays in the risky range.
"""

from __future__ import annotations

from app.decide import LABELS

SUPPORT_POINTS = {
    "official_process": 0.07,
    "eligibility_stated": 0.07,
    "named_rounds": 0.07,
    "careers_portal": 0.07,
    "compensation_stated": 0.06,
    "no_fee_stated": 0.05,
    "company_domain": 0.04,
    "role_stated": 0.04,
    "locations_stated": 0.04,
    "deadline_stated": 0.04,
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def offer_score(
    label: str,
    probabilities: dict[str, float],
    risks: list[dict],
    supports: list[dict],
) -> tuple[float, dict[str, float]]:
    if label not in LABELS:
        raise ValueError(f"Unknown label: {label}")

    high = [item for item in risks if item.get("severity") == "high"]
    medium = [item for item in risks if item.get("severity") == "medium"]
    boost = sum(SUPPORT_POINTS.get(item.get("id"), 0.03) for item in supports)
    model = float(probabilities.get(label, 0.0))

    if label == "risky":
        shown = _clip(max(model, 0.72) + 0.05 * len(high) + 0.03 * len(medium), 0.72, 0.96)
    elif label == "unclear":
        shown = _clip(0.38 + min(boost, 0.16) * 0.4 - 0.04 * len(high), 0.34, 0.58)
    elif boost < 0.12:
        shown = _clip(max(model, 0.48), 0.45, 0.64)
    else:
        ceiling = 0.92 if medium else 0.96
        shown = _clip(0.64 + min(boost, 0.30) - 0.04 * len(medium), 0.70, ceiling)

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
