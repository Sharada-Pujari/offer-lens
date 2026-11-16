"""Combine the model label with the quoted evidence.

The model is the main decision. A high-risk phrase the reader can see is
allowed to hold the result back from "credible", and two such phrases can
hold it at "risky" when the model is unsure.
"""

from __future__ import annotations

LABELS = ("risky", "unclear", "credible")


def decide(model_label: str, risk_signals: list[dict]) -> tuple[str, str | None]:
    if model_label not in LABELS:
        raise ValueError(f"Unknown model label: {model_label}")

    high = [item for item in risk_signals if item.get("severity") == "high"]
    if not high:
        return model_label, None
    if model_label == "risky":
        return "risky", None
    if len(high) >= 2:
        return (
            "risky",
            "Held at risky because the message contains more than one high-risk pattern.",
        )
    if model_label == "credible":
        return (
            "unclear",
            "Held at unclear because a high-risk pattern conflicts with the model.",
        )
    return "unclear", None


def summary(label: str) -> str:
    if label == "risky":
        return (
            "This message has the shape of a risky placement offer. "
            "Slow down before you reply, pay, or share documents."
        )
    if label == "credible":
        return (
            "This message looks like a normal campus process. "
            "Still confirm it with your placement office and the company careers page."
        )
    return (
        "This message does not show enough of a real process to trust yet. "
        "Ask for the official route before you treat it as an offer."
    )


def checklist(risk_signals: list[dict]) -> list[dict]:
    present = {item["id"] for item in risk_signals}
    rows = [
        (
            "domain",
            "Confirm the sender uses a company or college domain, not a free inbox.",
            "freemail" in present,
        ),
        (
            "fee",
            "Do not pay a fee, deposit, or refundable charge to receive an offer.",
            "upfront_payment" in present,
        ),
        (
            "identity",
            "Do not send Aadhaar, PAN, bank scans, or an OTP in chat.",
            "identity_documents" in present,
        ),
        (
            "writing",
            "Ask for the role, stipend, location, and interview rounds in writing.",
            True,
        ),
        (
            "office",
            "Check the careers page or ask your placement office before you share documents.",
            True,
        ),
        (
            "pressure",
            "Treat same-day pressure and limited seats as a reason to pause.",
            "urgency" in present,
        ),
        (
            "tasks",
            "Ignore guaranteed packages and tasks that need a payment before you can withdraw.",
            bool(present & {"guaranteed_outcome", "task_or_withdrawal"}),
        ),
        (
            "bond",
            "Read any service bond: the amount, the duration, and what happens if you leave.",
            "service_bond" in present,
        ),
    ]
    return [
        {"id": key, "text": text, "emphasis": emphasis}
        for key, text, emphasis in rows
    ]
