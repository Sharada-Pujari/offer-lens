from app.score import evidence_points, offer_score
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
CAMPUS = (
    "The placement office will hold an on-campus drive. Eligibility: CGPA 7.0 and no backlogs. "
    "Rounds: online test, technical round, HR round. The company does not charge any fee."
)
PARTIAL = "Company: Northwind. Role: Graduate Engineer Trainee. Eligibility: CGPA 7.0. Apply on the careers page."
THIN = "Startup in Pune is hiring interns. Ping me for details."
FEE = (
    "Pay a refundable registration fee of Rs 1499 and send your Aadhaar photo. "
    "Mail hr.hiring@gmail.com."
)


def _score(label: str, probabilities: dict, text: str) -> float:
    risks, supports = extract_signals(text)
    score, shares = offer_score(label, probabilities, risks, supports, text)
    assert shares[label] == score
    assert abs(sum(shares.values()) - 1.0) < 0.001
    return score


def test_each_added_fact_raises_the_score():
    thin_points = evidence_points(THIN)
    partial_points = evidence_points(PARTIAL)
    campus_points = evidence_points(CAMPUS)
    drive_points = evidence_points(DRIVE)
    assert thin_points < partial_points < campus_points < drive_points


def test_notices_do_not_share_one_percentage():
    model = {"risky": 0.30, "unclear": 0.28, "credible": 0.42}
    partial = _score("credible", model, PARTIAL)
    campus = _score("credible", model, CAMPUS)
    drive = _score("credible", model, DRIVE)
    assert partial < campus < drive
    assert drive - partial >= 0.08
    assert campus - partial >= 0.04
    assert drive < 0.96


def test_a_fee_and_identity_request_stays_a_high_risk_score():
    risks, supports = extract_signals(FEE)
    score, shares = offer_score(
        "risky",
        {"risky": 0.51, "unclear": 0.27, "credible": 0.22},
        risks,
        supports,
        FEE,
    )
    assert score >= 0.80
    assert shares["risky"] == score
    assert shares["risky"] > shares["credible"]


def test_a_thin_message_does_not_look_like_a_complete_offer():
    score, _shares = offer_score(
        "unclear",
        {"risky": 0.2, "unclear": 0.5, "credible": 0.3},
        [],
        [],
        THIN,
    )
    assert score <= 0.45
