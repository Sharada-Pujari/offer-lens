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


DRIVE = (
    "Company: L&T Technology Services. Role: Associate Engineer Trainee. "
    "CTC: ₹4 LPA. packege : ₹25,000/month for the first 3 months. "
    "Locations: Hyderabad, Pune and Mumbai. "
    "Eligibility Criteria: Minimum 60% or 6.75 CGPA. "
    "Selection Process: Technical Interview and HR Interview. "
    "Mandatory undertaking/bond of ₹2 Lakhs for 2 years. "
    "Last Date to Apply: 30 November 2026."
)


def test_stipend_question_quotes_the_pay_and_not_a_fee():
    reply = answer(_analysis("credible"), "what is the stipend?", DRIVE)
    assert "25,000" in reply
    assert "not a fee" in reply
    assert "marked credible" in reply


def test_other_questions_are_not_copies_of_each_other():
    analysis = _analysis("credible")
    analysis["risk_signals"] = [
        {
            "id": "service_bond",
            "severity": "medium",
            "title": "Mentions a service bond",
            "detail": "Read the amount and the duration.",
            "excerpt": "bond of ₹2 Lakhs",
        }
    ]
    apply = answer(analysis, "Should I apply?", DRIVE)
    legit = answer(analysis, "is it legit", DRIVE)
    bond = answer(analysis, "what about the bond?", DRIVE)
    places = answer(analysis, "which city?", DRIVE)
    assert apply != legit
    assert "2 Lakhs" in bond
    assert "Hyderabad" in places
    assert bond != apply


def test_clear_process_still_points_at_the_official_route():
    reply = answer(_analysis("credible"), "Should I apply?")
    assert "marked credible" in reply
    assert "placement office" in reply
