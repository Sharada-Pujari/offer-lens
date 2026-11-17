import anyio
import httpx

from app.main import MODEL_PATH, app
from app.predictor import Predictor
from app.sessions import SessionStore

app.state.predictor = Predictor.load(MODEL_PATH)
app.state.sessions = SessionStore()

SCAM = (
    "Dear student, you are selected. Pay a refundable registration fee of Rs 1499 "
    "and send your Aadhaar photo on WhatsApp. Mail hr.hiring@gmail.com. "
    "Limited seats. Offer expires tonight."
)
CAMPUS = (
    "The placement office will hold an on-campus drive. Eligibility: CGPA 7.0 "
    "and no active backlogs. Rounds: online test, technical round, HR round. "
    "Register with your college email. The company does not charge any fee."
)


def request(method: str, path: str, json=None) -> httpx.Response:
    async def _call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=json)

    return anyio.run(_call)


def test_filler_pairs_are_not_displayed_phrases():
    from app.predictor import _keep_cue

    assert not _keep_cue("on the")
    assert not _keep_cue("in the")
    assert _keep_cue("cgpa")


def test_displayed_phrases_skip_weak_fragments():
    _label, _confidence, _probabilities, cues = app.state.predictor.predict(SCAM)
    assert "com" not in cues
    assert "the" not in cues
    assert cues


def test_health():
    response = request("GET", "/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_page_loads():
    response = request("GET", "/")
    assert response.status_code == 200
    assert "Offer Lens" in response.text


def test_risky_message_is_not_called_credible():
    response = request("POST", "/api/analyze", json={"text": SCAM})
    body = response.json()
    assert response.status_code == 200
    assert body["label"] == "risky"
    assert "session_id" in body
    ids = {item["id"] for item in body["risk_signals"]}
    assert "upfront_payment" in ids
    assert "identity_documents" in ids


def test_campus_notice_is_credible_and_chat_remembers_it():
    response = request("POST", "/api/analyze", json={"text": CAMPUS})
    body = response.json()
    assert response.status_code == 200
    assert body["label"] == "credible"
    chat = request(
        "POST",
        "/api/chat",
        json={"session_id": body["session_id"], "message": "Should I apply?"},
    )
    assert chat.status_code == 200
    assert chat.json()["remembered_label"] == "credible"
    assert "marked credible" in chat.json()["reply"]


def test_chat_without_an_offer_is_rejected():
    response = request(
        "POST",
        "/api/chat",
        json={"session_id": "missing-session-id", "message": "Should I apply?"},
    )
    assert response.status_code == 404


def test_empty_message_is_rejected():
    response = request("POST", "/api/analyze", json={"text": "   "})
    assert response.status_code == 422


DRIVE = (
    "L&T Technology Services has officially opened its GET Off Campus Drive 2026 "
    "through Superset. Role: Associate Engineer Trainee. CTC: ₹4 LPA. "
    "packege : ₹25,000/month for the first 3 months. Job Type: Full-Time. "
    "Locations: Bangalore, Chennai, Mysore, Hyderabad, Pune, Mumbai, Vadodara & Delhi. "
    "Eligibility Criteria: Minimum 60% or 6.75 CGPA in 10th, 12th & Graduation. "
    "No active backlogs. Must clear final-year examinations in the first attempt. "
    "Selection Process: 1. Technical Interview 2. HR Interview. "
    "3 months of classroom training followed by 12 months of on-the-job training. "
    "Mandatory undertaking/bond of ₹2 Lakhs for 2 years and 9 months. "
    "Last Date to Apply: 30 November 2026."
)


def test_complete_off_campus_drive_scores_with_the_notice():
    response = request("POST", "/api/analyze", json={"text": DRIVE})
    body = response.json()
    assert response.status_code == 200
    assert body["label"] == "credible"
    assert body["score"] >= 0.85
    assert body["shares"]["credible"] == body["score"]
    assert body["confidence"] < body["score"]
