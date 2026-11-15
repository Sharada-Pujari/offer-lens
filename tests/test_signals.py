from app.decide import decide
from app.signals import extract_signals


FEE_AND_ID = (
    "Pay a refundable registration fee of Rs 1499 and send your Aadhaar photo. "
    "Mail hr.hiring@gmail.com."
)
CAMPUS = (
    "The placement office listed a drive. Eligibility is CGPA 7.0 with no backlogs. "
    "Rounds: online test, technical round, HR round. No fee is charged."
)


def test_quoted_lines_are_slices_of_the_message():
    risks, supports = extract_signals(FEE_AND_ID)
    compact = " ".join(FEE_AND_ID.split())
    for item in risks + supports:
        assert item["excerpt"].strip("…") in compact


def test_payment_and_identity_are_high_risk():
    risks, _supports = extract_signals(FEE_AND_ID)
    found = {item["id"]: item["severity"] for item in risks}
    assert found["upfront_payment"] == "high"
    assert found["identity_documents"] == "high"
    assert found["freemail"] == "medium"


def test_campus_notice_has_support_and_no_high_risk():
    risks, supports = extract_signals(CAMPUS)
    assert not any(item["severity"] == "high" for item in risks)
    support_ids = {item["id"] for item in supports}
    assert "official_process" in support_ids
    assert "no_fee_stated" in support_ids


def test_two_high_patterns_hold_a_credible_model_at_risky():
    risks, _supports = extract_signals(FEE_AND_ID)
    label, note = decide("credible", risks)
    assert label == "risky"
    assert note


def test_one_high_pattern_holds_a_credible_model_at_unclear():
    risks, _supports = extract_signals("Please pay the registration fee of Rs 500.")
    label, note = decide("credible", risks)
    assert label == "unclear"
    assert note


def test_rupees_and_national_id_are_quoted():
    risks, _supports = extract_signals(
        "Transfer 2200 rupees for the joining kit and upload your national ID."
    )
    found = {item["id"] for item in risks}
    assert "upfront_payment" in found
    assert "identity_documents" in found


def test_model_label_stands_when_nothing_high_is_quoted():
    label, note = decide("credible", [])
    assert label == "credible"
    assert note is None
