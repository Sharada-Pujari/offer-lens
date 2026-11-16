"""Answer questions about the offer that was just checked.

Replies stay on that message. They use the decision, the quoted patterns,
and the words in the offer. They do not browse the web and they do not
invent a company.
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
    "guaranteed_outcome": ("guaranteed", "no interview"),
    "service_bond": ("bond", "undertaking"),
}

# Question words, then the words to look for in the offer.
TOPICS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("pay", ("stipend", "salary", "ctc", "package", "packege", "lpa", "compensation", "inhand"), ("ctc", "stipend", "salary", "package", "packege", "lpa", "/month", "per month")),
    ("bond", ("bond", "undertaking", "lockin"), ("bond", "undertaking")),
    ("eligibility", ("eligibility", "eligible", "cgpa", "qualification", "criteria", "backlog", "backlogs", "percent", "graduation"), ("eligib", "cgpa", "backlog", "60%", "graduation")),
    ("location", ("location", "locations", "city", "cities", "where is", "which city"), ("location", "bangalore", "chennai", "mysore", "hyderabad", "pune", "mumbai", "vadodara", "delhi")),
    ("rounds", ("round", "rounds", "interview", "selection", "process"), ("interview", "round", "selection")),
    ("deadline", ("deadline", "lastdate"), ("last date", "deadline")),
    ("role", ("role", "position", "company", "hiring"), ("role", "company")),
)

TOPIC_LEAD = {
    "pay": "The pay stated in this message is",
    "bond": "The bond stated in this message is",
    "eligibility": "The eligibility stated in this message is",
    "location": "The locations stated in this message are",
    "rounds": "The selection steps stated in this message are",
    "deadline": "The date stated in this message is",
    "role": "The role stated in this message is",
}

QUESTION_STOP = {
    "the", "and", "for", "you", "your", "what", "whats", "about", "this", "that",
    "with", "from", "tell", "does", "did", "how", "can", "will", "are", "was",
    "have", "has", "its", "any", "there", "please", "give", "want", "know",
    "much", "many", "when", "who", "which", "into", "they", "them", "then",
}


def answer(analysis: dict, question: str, offer_text: str = "") -> str:
    label = analysis["label"]
    prefix = f"About the offer marked {label}: "
    intent = _intent(question)
    topic = _topic(question)

    if intent == "draft_reply":
        return prefix + _draft(label, analysis["risk_signals"])
    if intent == "what_to_verify":
        return prefix + _verify(analysis["checklist"])
    if intent == "why_flagged":
        signal = _matching_signal(question)
        if signal:
            return prefix + _explain_signal(signal, analysis["risk_signals"])
        return prefix + _why(analysis)
    if topic:
        return prefix + _about_topic(topic, offer_text)
    if intent == "legit":
        return prefix + _legit(analysis, offer_text)
    if intent == "should_i_apply":
        return prefix + _should(label, analysis)
    signal = _matching_signal(question)
    if signal:
        return prefix + _explain_signal(signal, analysis["risk_signals"])
    quoted = _overlap(question, offer_text)
    if quoted:
        return prefix + f"The closest line in this message is: “{quoted}”."
    return prefix + _inventory(offer_text)


def _intent(question: str) -> str:
    text = question.lower()
    rules = (
        ("draft_reply", ("draft", "reply", "respond", "write back", "what do i say", "what should i say")),
        ("what_to_verify", ("verify", "checklist", "what should i check", "next step", "how do i check", "placement office")),
        ("why_flagged", ("why", "flag", "explain", "score", "what is wrong", "reason")),
        ("legit", ("legit", "genuine", "fake", "scam", "real or not")),
        ("should_i_apply", ("should i apply", "should i go", "can i trust", "is this safe", "is it safe")),
    )
    for name, keys in rules:
        if any(key in text for key in keys):
            return name
    return "general"


def _has_term(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return term in TOKEN_RE.findall(text)


def _topic(question: str) -> str | None:
    text = question.lower().replace("-", "")
    for name, questions, _offer_terms in TOPICS:
        if any(_has_term(text, word) for word in questions):
            return name
    if "last date" in text or "apply by" in text:
        return "deadline"
    if _has_term(text, "pay") and not any(_has_term(text, word) for word in ("fee", "fees", "deposit", "charge")):
        return "pay"
    return None


def _matching_signal(question: str) -> str | None:
    text = question.lower()
    for signal_id, words in SIGNAL_WORDS.items():
        if any(_has_term(text, word) for word in words):
            return signal_id
    return None


def _window(text: str, start: int, end: int) -> str:
    left = max(0, start - 36)
    right = min(len(text), end + 88)
    if left > 0:
        gap = text.find(" ", left)
        if 0 <= gap < start:
            left = gap + 1
    if right < len(text):
        gap = text.rfind(" ", end, right)
        if gap > end:
            right = gap
    snippet = " ".join(text[left:right].split())
    if left > 0:
        snippet = "…" + snippet
    if right < len(text):
        snippet = snippet + "…"
    return snippet


def _find_term(text: str, terms: tuple[str, ...]) -> str | None:
    lower = text.lower()
    for term in terms:
        at = lower.find(term.lower())
        if at >= 0:
            return _window(text, at, at + len(term))
    return None


def _about_topic(topic: str, offer_text: str) -> str:
    terms = next(item[2] for item in TOPICS if item[0] == topic)
    quoted = _find_term(offer_text, terms) if offer_text else None
    lead = TOPIC_LEAD[topic]
    if quoted is None:
        return f"This message does not state the {topic}."
    extra = ""
    if topic == "pay":
        extra = " That is pay for the role, not a fee you send to receive the offer."
    elif topic == "bond":
        extra = " A bond is a commitment after you join. It is different from a registration fee."
    return f"{lead}: “{quoted}”.{extra}"


def _explain_signal(signal_id: str, risk_signals: list[dict]) -> str:
    found = next((item for item in risk_signals if item["id"] == signal_id), None)
    if found is None:
        return "I did not see that pattern in this same offer."
    return (
        f"The line behind “{found['title']}” was: “{found['excerpt']}”. "
        f"{found['detail']}"
    )


def _should(label: str, analysis: dict) -> str:
    bond = any(item["id"] == "service_bond" for item in analysis["risk_signals"])
    if label == "risky":
        text = (
            "I would not apply from this message alone. "
            "Talk to your placement office before you pay anyone or send documents."
        )
    elif label == "credible":
        text = (
            "It reads like a normal process. "
            "Apply only through the placement office or the careers page named in the message."
        )
    else:
        text = (
            "I would not treat this as an offer yet. "
            "Ask who is hiring, what the rounds are, and which official email will confirm it."
        )
    if bond:
        text += " Read the service bond in the message before you decide: the amount and the duration."
    return text


def _legit(analysis: dict, offer_text: str) -> str:
    high = [item["title"].lower() for item in analysis["risk_signals"] if item.get("severity") == "high"]
    if high:
        return (
            "I would not call it legitimate from this message alone. "
            f"High-risk lines: {', '.join(high)}."
        )
    bond = _find_term(offer_text, ("bond", "undertaking")) if offer_text else None
    if analysis["label"] == "credible":
        text = (
            "The wording looks like a drive notice, and I did not see a fee or an identity-document request. "
            "That still does not prove the sender is the company. Use the portal or the office named in the message."
        )
    else:
        text = "I cannot call it legitimate from this message alone. Too little of a real process is written down."
    if bond:
        text += f" It does mention a bond: “{bond}”."
    return text


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
    if "service_bond" in present:
        limits.append("Please confirm the bond amount, the duration, and what happens if I leave.")
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


def _overlap(question: str, offer_text: str) -> str | None:
    if not offer_text:
        return None
    words = [
        word for word in TOKEN_RE.findall(question.lower())
        if len(word) > 3 and word not in QUESTION_STOP
    ]
    return _find_term(offer_text, tuple(words))


def _inventory(offer_text: str) -> str:
    if not offer_text:
        return (
            "Ask about the pay, the bond, the eligibility, the locations, or the rounds. "
            "I will answer from this offer."
        )
    found = []
    for name, _questions, terms in TOPICS:
        if _find_term(offer_text, terms):
            found.append(name)
    if not found:
        return "This message is too short for me to pull a specific line. Ask what you want checked."
    listed = ", ".join(found)
    return f"I can answer from this message. It mentions {listed}. Ask about one of those."
