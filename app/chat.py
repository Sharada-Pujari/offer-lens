"""Answer questions about the offer that was just checked.

Replies stay on that message. They use the decision, the quoted patterns,
and the checklist. They do not browse the web and they do not invent a company.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

SIGNAL_WORDS: dict[str, tuple[str, ...]] = {
    "upfront_payment": ("fee", "fees", "pay", "payment", "deposit", "money", "charge", "qr"),
    "identity_documents": ("aadhaar", "aadhar", "pan", "passport", "otp", "document", "cheque", "passbook"),
    "task_or_withdrawal": ("task", "withdraw", "withdrawal", "rating", "wallet"),
    "freemail": ("gmail", "yahoo", "hotmail", "outlook", "email", "mail"),
    "urgency": ("urgent", "today", "tonight", "expires", "limited", "seat", "hurry"),
    "unofficial_channel": ("whatsapp", "telegram", "dm"),
    "guaranteed_outcome": ("guaranteed", "package", "lpa", "no interview"),
}


def answer(analysis: dict, question: str) -> str:
    label = analysis["label"]
    prefix = f"About the offer marked {label}: "
    signal = _matching_signal(question)
    intent = _intent(question)

    if signal and intent in {"general", "why_flagged"}:
        return prefix + _explain_signal(signal, analysis["risk_signals"])
    if intent == "draft_reply":
        return prefix + _draft(label, analysis["risk_signals"])
    if intent == "what_to_verify":
        return prefix + _verify(analysis["checklist"])
    if intent == "why_flagged":
        return prefix + _why(analysis)
    if intent == "should_i_apply":
        return prefix + _should(label)
    if signal:
        return prefix + _explain_signal(signal, analysis["risk_signals"])
    return (
        prefix
        + "Ask me whether to apply, why it was marked this way, what to verify, "
        + "or for a reply you can send. I will stay on this offer."
    )


def _intent(question: str) -> str:
    text = question.lower()
    rules = (
        ("draft_reply", ("draft", "reply", "respond", "write back", "what do i say", "what should i say")),
        ("what_to_verify", ("verify", "checklist", "what should i check", "next step", "how do i check", "placement office")),
        ("why_flagged", ("why", "flag", "explain", "score", "what is wrong", "reason")),
        ("should_i_apply", ("should i apply", "should i go", "can i trust", "is this safe", "is it safe", "legit", "genuine")),
    )
    for name, keys in rules:
        if any(key in text for key in keys):
            return name
    return "general"


def _has_term(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return term in TOKEN_RE.findall(text)


def _matching_signal(question: str) -> str | None:
    text = question.lower()
    for signal_id, words in SIGNAL_WORDS.items():
        if any(_has_term(text, word) for word in words):
            return signal_id
    return None


def _explain_signal(signal_id: str, risk_signals: list[dict]) -> str:
    found = next((item for item in risk_signals if item["id"] == signal_id), None)
    if found is None:
        return "I did not see that pattern in this same offer."
    return (
        f"The line behind “{found['title']}” was: “{found['excerpt']}”. "
        f"{found['detail']}"
    )


def _should(label: str) -> str:
    if label == "risky":
        return (
            "I would not apply from this message alone. "
            "Talk to your placement office before you pay anyone or send documents."
        )
    if label == "credible":
        return (
            "It reads like a normal process. "
            "Apply only through the placement office or the careers page named in the message."
        )
    return (
        "I would not treat this as an offer yet. "
        "Ask who is hiring, what the rounds are, and which official email will confirm it."
    )


def _why(analysis: dict) -> str:
    titles = [item["title"].lower() for item in analysis["risk_signals"]]
    if titles:
        joined = "; ".join(titles)
        return f"The check marked it {analysis['label']} and quoted these patterns: {joined}."
    cues = ", ".join(analysis.get("cues") or [])
    if cues:
        return (
            f"The check marked it {analysis['label']}. "
            f"The model leaned on these phrases in the message: {cues}."
        )
    return f"The check marked it {analysis['label']} because the wording is thin."


def _verify(items: list[dict]) -> str:
    ordered = sorted(items, key=lambda item: not item["emphasis"])
    lines = [f"{index}. {item['text']}" for index, item in enumerate(ordered, start=1)]
    return "Check these before you reply:\n" + "\n".join(lines)


def _draft(label: str, risk_signals: list[dict]) -> str:
    present = {item["id"] for item in risk_signals}
    limits: list[str] = []
    if "upfront_payment" in present or "task_or_withdrawal" in present:
        limits.append("I will not pay a fee or a deposit to receive an offer.")
    if "identity_documents" in present:
        limits.append("I will not send identity documents or an OTP in this chat.")
    limit_text = " ".join(limits)
    if label == "credible":
        body = (
            "Thank you. I will apply through the placement office or the careers "
            "page in your message. Please confirm the role, the stipend, the rounds, "
            "and that there is no fee."
        )
    else:
        body = (
            "Thank you for the message. Before I proceed, please send the role, "
            "stipend, and process from a company or college email. "
            "I am checking this with my placement office."
        )
    tail = f" {limit_text}" if limit_text else ""
    return f"You could send this:\n\nHello,\n\n{body}{tail}\n\nThank you."
