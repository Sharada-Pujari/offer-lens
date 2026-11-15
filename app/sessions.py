"""Remember one checked offer for the follow-up chat."""

from __future__ import annotations

import threading
from uuid import uuid4


class SessionStore:
    def __init__(self, limit: int = 300):
        self._limit = limit
        self._lock = threading.Lock()
        self._items: dict[str, dict] = {}

    def create(self, text: str, analysis: dict) -> str:
        session_id = uuid4().hex
        with self._lock:
            self._items[session_id] = {
                "text": text,
                "analysis": analysis,
                "messages": [],
            }
            while len(self._items) > self._limit:
                oldest = next(iter(self._items))
                self._items.pop(oldest, None)
        return session_id

    def get(self, session_id: str) -> dict | None:
        with self._lock:
            item = self._items.get(session_id)
            return None if item is None else {
                "text": item["text"],
                "analysis": item["analysis"],
                "messages": list(item["messages"]),
            }

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            item = self._items.get(session_id)
            if item is None:
                raise KeyError(session_id)
            item["messages"].append({"role": role, "content": content})
