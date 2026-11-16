"""Load the trained text classifier and show the phrases it used."""

from __future__ import annotations

from pathlib import Path

import joblib

from app.decide import LABELS

# Fragments that show up in almost every message. They are weak to display.
WEAK_WORDS = {
    "on",
    "in",
    "of",
    "to",
    "at",
    "by",
    "or",
    "as",
    "be",
    "is",
    "it",
    "an",
    "a",
}
SKIP_CUES = {
    "the",
    "and",
    "for",
    "you",
    "your",
    "this",
    "that",
    "with",
    "from",
    "are",
    "was",
    "com",
    "www",
    "http",
    "https",
    "not",
    "any",
    "has",
    "have",
    "will",
    "its",
    "our",
    "but",
    "can",
    "all",
}


def _keep_cue(term: str) -> bool:
    if term in SKIP_CUES or len(term) < 3 or not any(character.isalpha() for character in term):
        return False
    parts = term.split()
    return any(part not in WEAK_WORDS and part not in SKIP_CUES for part in parts)


class Predictor:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        classes = list(pipeline.named_steps["clf"].classes_)
        missing = [label for label in LABELS if label not in classes]
        if missing:
            raise ValueError(f"Model is missing labels: {missing}")

    @classmethod
    def load(cls, path: Path) -> "Predictor":
        if not path.exists():
            raise FileNotFoundError(
                f"No model at {path}. From the project folder run: python train.py"
            )
        return cls(joblib.load(path))

    def predict(self, text: str) -> tuple[str, float, dict[str, float], list[str]]:
        classifier = self.pipeline.named_steps["clf"]
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = list(classifier.classes_)
        scored = {label: float(probabilities[index]) for index, label in enumerate(classes)}
        label = max(scored, key=scored.get)
        cues = self._cues(text, label)
        return label, scored[label], scored, cues

    def _cues(self, text: str, label: str, limit: int = 5) -> list[str]:
        vectoriser = self.pipeline.named_steps["tfidf"]
        classifier = self.pipeline.named_steps["clf"]
        matrix = vectoriser.transform([text])
        names = vectoriser.get_feature_names_out()
        class_index = list(classifier.classes_).index(label)
        weights = classifier.coef_[class_index]
        ranked: list[tuple[float, str]] = []
        for index in matrix.nonzero()[1]:
            term = str(names[index])
            if not _keep_cue(term):
                continue
            ranked.append((float(weights[index] * matrix[0, index]), term))
        ranked.sort(reverse=True)
        cues: list[str] = []
        for _score, term in ranked:
            if term not in cues:
                cues.append(term)
            if len(cues) == limit:
                break
        return cues
