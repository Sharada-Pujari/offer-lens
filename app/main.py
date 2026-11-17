"""HTTP API and the Offer Lens page."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import __version__
from app.chat import answer
from app.decide import checklist, decide, summary
from app.predictor import Predictor
from app.score import offer_score
from app.sessions import SessionStore
from app.signals import extract_signals

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "offer_clf.joblib"

EXAMPLES = [
    {
        "id": "risky",
        "title": "Fee and documents",
        "text": (
            "Dear student, you are selected for a work-from-home internship. "
            "Pay a refundable registration fee of Rs 1499 today and send your "
            "Aadhaar photo on WhatsApp. Limited seats. Mail hr.hiring@gmail.com."
        ),
    },
    {
        "id": "credible",
        "title": "Campus notice",
        "text": (
            "The placement office will hold an on-campus drive on 18 March. "
            "Eligibility: CGPA 7.0 and no active backlogs. Rounds: online test, "
            "technical round, HR round. Register on the link from the placement cell. "
            "The company does not charge any fee."
        ),
    },
    {
        "id": "unclear",
        "title": "Too little detail",
        "text": "Startup in Pune is hiring interns. Ping me for details.",
    },
]


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=1000)


def build_analysis(predictor: Predictor, text: str) -> dict:
    model_label, confidence, probabilities, cues = predictor.predict(text)
    risks, supports = extract_signals(text)
    label, note = decide(model_label, risks)
    score, shares = offer_score(label, probabilities, risks, supports)
    return {
        "label": label,
        "model_label": model_label,
        "confidence": round(confidence, 3),
        "score": score,
        "probabilities": {key: round(value, 3) for key, value in probabilities.items()},
        "shares": shares,
        "override_note": note,
        "summary": summary(label),
        "risk_signals": risks,
        "support_signals": supports,
        "cues": cues,
        "checklist": checklist(risks),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.predictor = Predictor.load(MODEL_PATH)
    app.state.sessions = SessionStore()
    yield


app = FastAPI(title="Offer Lens", version=__version__, lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.post("/api/analyze")
def analyze(body: AnalyzeRequest):
    text = " ".join(body.text.split())
    if not text:
        raise HTTPException(status_code=422, detail="Paste the offer message first.")
    analysis = build_analysis(app.state.predictor, text)
    session_id = app.state.sessions.create(text, analysis)
    return {"session_id": session_id, **analysis}


@app.post("/api/chat")
def chat(body: ChatRequest):
    stored = app.state.sessions.get(body.session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Check an offer before asking about it.")
    reply = answer(stored["analysis"], body.message.strip(), stored["text"])
    app.state.sessions.add_message(body.session_id, "user", body.message.strip())
    app.state.sessions.add_message(body.session_id, "assistant", reply)
    return {
        "session_id": body.session_id,
        "reply": reply,
        "remembered_label": stored["analysis"]["label"],
    }


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
