"""Reference documents and a small BM25 retriever (stdlib only)."""
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List

from guardrails.groundedness import content_tokens

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str


class KnowledgeBase:
    def __init__(self, path: Path = DEFAULT_PATH, k1: float = 1.5, b: float = 0.75):
        with open(path, encoding="utf-8") as f:
            self.docs = [Document(**d) for d in json.load(f)]
        self.by_id = {d.id: d for d in self.docs}
        self._tf = [Counter(self._tokens(d)) for d in self.docs]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = sum(self._len) / len(self._len)
        df = Counter(t for tf in self._tf for t in tf)
        n = len(self.docs)
        self._idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.k1, self.b = k1, b

    @staticmethod
    def _tokens(doc: Document) -> List[str]:
        # Title counted twice so it weighs more than body text.
        return list(content_tokens(doc.title)) * 2 + [t for t in _all_tokens(doc.text)]

    def search(self, query: str, k: int = 3, min_score: float = 1.0) -> List[Document]:
        q = content_tokens(query)
        scored = []
        for i, tf in enumerate(self._tf):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self._idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self._len[i] / self._avg))
            if s >= min_score:
                scored.append((s, self.docs[i]))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:k]]


def _all_tokens(text: str) -> List[str]:
    # content_tokens returns a set; keep duplicates for term frequency.
    return [t for w in re.findall(r"[A-Za-z']+", text) for t in content_tokens(w)]
