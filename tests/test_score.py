from app.score import offer_score
from app.signals import extract_signals

DRIVE = (
    "L&T Technology Services opened its GET Off Campus Drive 2026 through Superset. "
    "Role: Associate Engineer Trainee. CTC: ₹4 LPA. packege : ₹25,000/month for the first 3 months. "
    "Locations: Hyderabad, Pune, Mumbai, Vadodara and Delhi. "
    "Eligibility Criteria: Minimum 60% or 6.75 CGPA in 10th, 12th and Graduation. "
    "No active backlogs. Selection Process: 1. Technical Interview 2. HR Interview. "
    "Mandatory undertaking/bond of ₹2 Lakhs for 2 years and 9 months. "
    "Last Date to Apply: 30 November 2026."
)

FEE = (
    "Pay a refundable registration fee of Rs 1499 and send your Aadhaar photo. "
    "Mail hr.hiring@gmail.com."
)


def test_a_complete_drive_scores_from_the_quoted_lines():
    risks, supports = extract_signals(DRIVE)
    # The text model can split a long notice near 44 / 29 / 28 and still be right.
    score, shares = offer_score(
        "credible",
        {"risky": 0.29, "unclear": 0.28, "credible": 0.44},
        risks,
        supports,
    )
    assert score >= 0.85
    assert shares["credible"] == score
    assert shares["credible"] > shares["risky"]
    assert shares["credible"] > shares["unclear"]
    assert abs(sum(shares.values()) - 1.0) < 0.001


def test_a_fee_and_identity_request_stays_a_high_risk_score():
    risks, supports = extract_signals(FEE)
    score, shares = offer_score(
        "risky",
        {"risky": 0.51, "unclear": 0.27, "credible": 0.22},
        risks,
        supports,
    )
    assert score >= 0.72
    assert shares["risky"] == score
    assert shares["risky"] > shares["credible"]


def test_a_thin_message_does_not_look_like_a_complete_offer():
    score, shares = offer_score(
        "unclear",
        {"risky": 0.2, "unclear": 0.5, "credible": 0.3},
        [],
        [],
    )
    assert score <= 0.58
    assert shares["unclear"] == score
