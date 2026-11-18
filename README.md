# Offer Lens

Offer Lens checks a placement message before a student replies to it.

Students and job seekers get job posts in WhatsApp groups, on Telegram, and as forwarded text. Some are real campus drives. Some ask for a fee, an Aadhaar photo, or a payment before a "withdrawal" unlocks. The usual check is to ask a senior in the same chat.

Paste the message. The app returns a label, the lines that drove it, a short checklist, and a chat that answers only about that message.

## What you can do with it

- Score a message as risky, unclear, or credible.
- Read the exact phrase behind each warning.
- See which phrases the text model used.
- Ask whether to apply, why it was marked that way, what to verify, or for a reply you can send.

The chat remembers the offer you just checked. It does not search the web, and it does not claim a company is real.

## How a decision is made

1. A TF-IDF model (word and two-word phrases) plus logistic regression scores the whole message. Training text is in `data/corpus.py`. Those messages were written for this project. They imitate real patterns. They are not copied from anyone's private chats.
2. Pattern checks quote lines a person can see: a fee, an identity document, a free email domain, a placement-office process, and similar signs.
3. The model is the main label. If the message contains a high-risk line, the result is held back from "credible". Two high-risk lines can hold an unsure result at "risky". A salary, CTC, or monthly stipend is pay for the role, not a fee. A service bond is quoted on its own and does not, by itself, force the label to risky.
4. The offer score on the page is not the raw class percentage. A long notice can split near 40 percent across the three classes even when the label is credible, which is why different offers were showing 44 and 42. Each fact in the message moves the score: a role, pay, eligibility, rounds, cities, a last date, or an official form. A service bond lowers it. A fee or an identity request keeps the score on the risky side. The model still nudges the number, so the same checklist in different wording does not land on one identical score.

`models/metrics.json` records two checks, then the shipped model is fit on the full composed set:

- Holdout: 25% of the composed messages, macro F1 1.00 on 19 messages.
- Unseen: 8 messages in `data/eval_set.py` that are not in training, 8 of 8.

Those messages were written with distinct, obvious wording, so the scores show that the pipeline separates this set. They are not a measure of every chat a student will receive. New wording can slip through, and a short note from a real startup can look thin. Confirm the offer with your placement office.

## Run it

From this folder, on Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python train.py
uvicorn app.main:app --port 8077
```

Open http://127.0.0.1:8077

On macOS or Linux, create the virtual environment with `python3 -m venv .venv` and activate it with `source .venv/bin/activate`.

Docker:

```powershell
docker compose up --build
```

That serves the same app on port 8077.

## Tests

```powershell
pytest
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | App status |
| GET | `/api/examples` | Three messages you can try |
| POST | `/api/analyze` | `{ "text": "..." }` returns the decision and a session id |
| POST | `/api/chat` | `{ "session_id": "...", "message": "..." }` answers about that offer |

## Explain it in one minute

Students receive placement messages that are hard to judge quickly. Offer Lens is a small text classifier with quoted evidence. The model looks at the wording. The evidence layer shows the line, so a fee request cannot be waved through as credible. The chat is tied to the checked message, which keeps the answers on that offer.

## Layout

```
app/            API, evidence, decision rule, chat memory
data/corpus.py  composed training messages
train.py        fits the model and writes metrics
static/         the page
tests/          evidence, chat, and API checks
```
