from app.chat import answer


def _analysis(label="risky"):
    return {
        "label": label,
        "model_label": label,
        "cues": ["registration fee"],
        "risk_signals": [
            {
                "id": "upfront_payment",
                "severity": "high",
                "title": "Asks for a payment",
                "detail": "A real campus offer does not need a fee.",
                "excerpt": "registration fee of Rs 1499",
            }
        ],
        "checklist": [
            {"id": "fee", "text": "Do not pay a fee to receive an offer.", "emphasis": True},
            {"id": "office", "text": "Ask your placement office.", "emphasis": True},
        ],
    }


def test_follow_up_stays_on_the_same_offer():
    first = answer(_analysis(), "Should I apply?")
    second = answer(_analysis(), "What about the fee?")
    assert "marked risky" in first
    assert "placement office" in first
    assert "marked risky" in second
    assert "registration fee of Rs 1499" in second


def test_draft_refuses_payment_on_a_risky_offer():
    reply = answer(_analysis(), "Draft a reply")
    assert "will not pay" in reply
    assert "Hello" in reply


def test_clear_process_still_points_at_the_official_route():
    reply = answer(_analysis("credible"), "Should I apply?")
    assert "marked credible" in reply
    assert "placement office" in reply
