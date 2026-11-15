"""Train the placement-message classifier and write metrics next to it."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from data.corpus import RECORDS
from data.eval_set import EVAL_RECORDS

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "offer_clf.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
JSONL_PATH = ROOT / "data" / "offers.jsonl"


def build_pipeline() -> Pipeline:
    # Stop-word lists drop "no", which matters in "no fee".
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=7,
                ),
            ),
        ]
    )


def train() -> dict:
    texts = [row["text"] for row in RECORDS]
    labels = [row["label"] for row in RECORDS]
    counts = dict(Counter(labels))

    pipeline = build_pipeline()
    train_text, test_text, train_y, test_y = train_test_split(
        texts,
        labels,
        test_size=0.25,
        random_state=7,
        stratify=labels,
    )
    pipeline.fit(train_text, train_y)
    predicted = pipeline.predict(test_text)
    report = classification_report(test_y, predicted, output_dict=True, zero_division=0)
    labels_order = ["risky", "unclear", "credible"]
    matrix = confusion_matrix(test_y, predicted, labels=labels_order).tolist()

    # Fit again on every composed example so the shipped model has seen them.
    pipeline.fit(texts, labels)
    eval_text = [row["text"] for row in EVAL_RECORDS]
    eval_y = [row["label"] for row in EVAL_RECORDS]
    eval_predicted = pipeline.predict(eval_text)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    JSONL_PATH.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in RECORDS),
        encoding="utf-8",
    )

    metrics = {
        "records": len(RECORDS),
        "counts": counts,
        "holdout_size": len(test_y),
        "holdout_macro_f1": round(float(f1_score(test_y, predicted, average="macro")), 3),
        "holdout_accuracy": round(float(report["accuracy"]), 3),
        "labels": labels_order,
        "confusion_matrix": matrix,
        "per_label_f1": {
            label: round(float(report[label]["f1-score"]), 3)
            for label in labels_order
            if label in report
        },
        "unseen_messages": len(EVAL_RECORDS),
        "unseen_macro_f1": round(float(f1_score(eval_y, eval_predicted, average="macro")), 3),
        "unseen_correct": int(sum(pred == truth for pred, truth in zip(eval_predicted, eval_y))),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2))
