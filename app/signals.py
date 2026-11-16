"""Quote the lines in a message that a student should slow down for.

The classifier scores the whole message. These patterns are separate: they
point at a phrase the reader can see, and they stop a confident "credible"
label when the phrase is high risk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
FREEMAIL = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.in",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "rediffmail.com",
    "proton.me",
    "protonmail.com",
}


@dataclass(frozen=True)
class Pattern:
    id: str
    severity: str
    title: str
    detail: str
    regex: re.Pattern[str]
    kind: str  # "risk" or "support"


PATTERNS: tuple[Pattern, ...] = (
    Pattern(
        id="upfront_payment",
        severity="high",
        title="Asks for a payment",
        detail="A real campus offer does not need a fee, deposit, or kit charge before you start.",
        regex=re.compile(
            r"(?:registration|processing|training|platform|portfolio|certificate|kyc)\s+fees?"
            r"|security deposit"
            r"|refundable (?:fee|deposit)"
            r"|(?:pay|deposit|transfer|send)\s+(?:rs\.?|inr|₹)\s?\d"
            r"|fees?\s+of\s+(?:rs\.?|inr|₹)?\s?\d"
            r"|\d[\d,]*\s*rupees"
            r"|joining kit"
            r"|token amount"
            r"|\bupi\b"
            r"|scan (?:this )?qr"
            r"|payment screenshot",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="identity_documents",
        severity="high",
        title="Asks for identity or bank documents",
        detail="Do not send Aadhaar, PAN, passport, bank scans, or an OTP in a chat.",
        regex=re.compile(
            r"\b(?:aadhaar|aadhar|pan card|passport copy|national id|cancelled cheque|"
            r"canceled cheque|bank passbook|share (?:the |your )?otp|send (?:the |your )?otp|cvv)\b",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="task_or_withdrawal",
        severity="high",
        title="Looks like a task or withdrawal trap",
        detail="Paying to unlock a withdrawal, or rating products for a promised payout, is a common trap.",
        regex=re.compile(
            r"withdrawal fees?"
            r"|unlock (?:your |the )?withdrawal"
            r"|rate (?:hotels|products)"
            r"|complete \d+ tasks"
            r"|product-rating",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="service_bond",
        severity="medium",
        title="Mentions a service bond",
        detail="A bond is a promise to stay, or to pay if you leave. It is not a registration fee. Read the amount and the duration before you accept.",
        regex=re.compile(r"\bbond\b|\bundertaking\b", re.I),
        kind="risk",
    ),
    Pattern(
        id="guaranteed_outcome",
        severity="medium",
        title="Promises a guaranteed outcome",
        detail="A guaranteed package, a guaranteed job, or no interview is a reason to slow down.",
        regex=re.compile(
            r"guaranteed (?:placement|job|package|offer|certificate|ppo|internship)"
            r"|no interview"
            r"|earn\s+(?:rs\.?|₹)\s?\d[\d,]*\s*(?:per|a|/)\s*(?:day|week)",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="urgency",
        severity="medium",
        title="Pushes you to act today",
        detail="Same-day pressure and 'limited seats' are used to stop you from checking with the placement office.",
        regex=re.compile(
            r"limited seats"
            r"|only \d+ (?:seats|spots|openings)"
            r"|offer expires"
            r"|expires tonight"
            r"|last chance"
            r"|payment today"
            r"|within \d+ hours"
            r"|pay today",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="unofficial_channel",
        severity="medium",
        title="Keeps you on a private chat",
        detail="A process that lives only on WhatsApp or Telegram is harder to verify.",
        regex=re.compile(
            r"whatsapp only"
            r"|only on whatsapp"
            r"|ping me on whatsapp"
            r"|telegram"
            r"|do not contact the college",
            re.I,
        ),
        kind="risk",
    ),
    Pattern(
        id="official_process",
        severity="info",
        title="Mentions a placement office process",
        detail="A notice that goes through the placement cell is easier to confirm.",
        regex=re.compile(
            r"placement (?:office|cell|coordinator)"
            r"|training and placement"
            r"|\btpo@",
            re.I,
        ),
        kind="support",
    ),
    Pattern(
        id="eligibility_stated",
        severity="info",
        title="States eligibility",
        detail="CGPA, backlogs, or branch criteria read like a real drive notice.",
        regex=re.compile(r"\b(?:cgpa|backlogs?|eligib)", re.I),
        kind="support",
    ),
    Pattern(
        id="named_rounds",
        severity="info",
        title="Names the rounds",
        detail="A test and interview steps are what a normal process looks like.",
        regex=re.compile(
            r"technical round|technical interview|online test|hr round|hr interview|"
            r"selection process|aptitude|pre-placement",
            re.I,
        ),
        kind="support",
    ),
    Pattern(
        id="no_fee_stated",
        severity="info",
        title="Says there is no fee",
        detail="Still confirm that line with the placement office. It is a good sign when the rest of the process is official.",
        regex=re.compile(
            r"no fees?"
            r"|does not charge"
            r"|do not pay"
            r"|no payment"
            r"|no deposit"
            r"|free of cost"
            r"|will not ask you to pay"
            r"|without a (?:fee|payment)",
            re.I,
        ),
        kind="support",
    ),
    Pattern(
        id="careers_portal",
        severity="info",
        title="Points at a careers page or official form",
        detail="Apply where the company or the placement office published the role.",
        regex=re.compile(
            r"careers (?:page|portal)"
            r"|superset"
            r"|college email",
            re.I,
        ),
        kind="support",
    ),
    Pattern(
        id="compensation_stated",
        severity="info",
        title="States the pay",
        detail="CTC, a stipend, or a monthly amount describes the role. It is not a fee.",
        regex=re.compile(
            r"\b(?:ctc|stipend|salary|lpa|package|packege)\b|/month|per month",
            re.I,
        ),
        kind="support",
    ),
)


def _excerpt(text: str, start: int, end: int) -> str:
    left = max(0, start - 48)
    right = min(len(text), end + 64)
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


def _from_match(pattern: Pattern, text: str, match: re.Match[str]) -> dict:
    return {
        "id": pattern.id,
        "severity": pattern.severity,
        "title": pattern.title,
        "detail": pattern.detail,
        "excerpt": _excerpt(text, match.start(), match.end()),
    }


PAY_CONTEXT = re.compile(
    r"ctc|stipend|salary|package|packege|\blpa\b|per month|/month|a month|remuneration|in[- ]hand",
    re.I,
)
FEE_CONTEXT = re.compile(
    r"\bfees?\b|deposit|joining kit|token amount|\bupi\b|payment|refundable|\bqr\b",
    re.I,
)


def _is_stated_pay(text: str, match: re.Match[str]) -> bool:
    """A rupee amount next to CTC or a stipend is pay, not a demand for a fee."""
    left = max(0, match.start() - 72)
    right = min(len(text), match.end() + 72)
    window = text[left:right]
    return PAY_CONTEXT.search(window) is not None and FEE_CONTEXT.search(window) is None


def _first_match(pattern: Pattern, text: str) -> re.Match[str] | None:
    for match in pattern.regex.finditer(text):
        if pattern.id == "upfront_payment" and _is_stated_pay(text, match):
            continue
        return match
    return None


def extract_signals(text: str) -> tuple[list[dict], list[dict]]:
    risks: list[dict] = []
    supports: list[dict] = []
    seen: set[str] = set()

    for pattern in PATTERNS:
        match = _first_match(pattern, text)
        if not match or pattern.id in seen:
            continue
        seen.add(pattern.id)
        item = _from_match(pattern, text, match)
        if pattern.kind == "risk":
            risks.append(item)
        else:
            supports.append(item)

    for match in EMAIL_RE.finditer(text):
        domain = match.group(0).split("@", 1)[1].lower()
        if domain in FREEMAIL and "freemail" not in seen:
            seen.add("freemail")
            risks.append(
                {
                    "id": "freemail",
                    "severity": "medium",
                    "title": "Uses a free email address",
                    "detail": "Campus HR and placement offices write from a company or college domain.",
                    "excerpt": _excerpt(text, match.start(), match.end()),
                }
            )
        elif domain not in FREEMAIL and "company_domain" not in seen:
            seen.add("company_domain")
            supports.append(
                {
                    "id": "company_domain",
                    "severity": "info",
                    "title": "Uses an organisational email",
                    "detail": "A company or college domain is easier to check than a free inbox. Confirm the domain is real.",
                    "excerpt": _excerpt(text, match.start(), match.end()),
                }
            )
    return risks, supports
