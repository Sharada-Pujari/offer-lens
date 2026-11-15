"""Messages kept out of training.

train.py scores these after the model is fit. They are a small check that the
wording was not copied from the training set, not a claim about every real offer.
"""

from __future__ import annotations

EVAL_RECORDS: list[dict[str, str]] = [
    {
        "label": "risky",
        "text": (
            "Kindly transfer 2200 rupees as a joining kit cost before we share "
            "the appointment letter. Upload your national ID in this chat."
        ),
    },
    {
        "label": "risky",
        "text": (
            "Seat is blocked only after a token amount. Send the UPI payment "
            "and your Aadhaar crop tonight or the letter is cancelled."
        ),
    },
    {
        "label": "risky",
        "text": (
            "Our associate will release the stipend once you pay the refundable "
            "deposit. Share the OTP if your bank sends one. Telegram only."
        ),
    },
    {
        "label": "credible",
        "text": (
            "Circular from the placement cell: the form is on Superset, then "
            "aptitude and a technical round. Carry your college ID. Nobody collects money."
        ),
    },
    {
        "label": "credible",
        "text": (
            "people@northwind.example wrote to the placement office with the "
            "internship JD, the stipend, and the interview slot. No fee is mentioned."
        ),
    },
    {
        "label": "unclear",
        "text": "Hi, I am from hiring. Send your resume and we will tell you the stipend later.",
    },
    {
        "label": "unclear",
        "text": "There may be an opening next month. I will forward the details if they send them.",
    },
    {
        "label": "unclear",
        "text": "A senior posted that some firm wants interns. No company name yet.",
    },
]
