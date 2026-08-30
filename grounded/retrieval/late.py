"""Late-interaction retrieval (MaxSim), behind the retriever interface.

Single-vector (bi-encoder) retrieval compresses a document to one vector and
loses the token-level signal, which is why gte ranked "Salesforce" third and
read money-laundering as check-fraud. Late interaction keeps a vector per token
and scores by MaxSim: each query token finds its best-matching document token,
and the scores are summed. That preserves exact-term precision.

This uses the embedding model's token vectors (no new dependency); a
ColBERT-trained checkpoint (via pylate / ragatouille) is a drop-in swap and is
the right move at large corpus scale.
"""
import numpy as np

from ..text import tokenize
from ..grounding import finalize
from .dense import DENSE_MODEL

LATE_THRESHOLD = 0.81   # calibrated on the eval (max correct at zero-wrong)


def _to_numpy(e):
    # token embeddings can come back as tensors on a GPU/MPS device
    if hasattr(e, "cpu"):
        e = e.cpu().numpy()
    return np.asarray(e, dtype="float32")


def _normalize_rows(m):
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


class LateInteractionIndex:
    token_gate = False
    threshold = LATE_THRESHOLD

    def __init__(self, items, model=None):
        self.items = items
        self.strong_tokens = set()
        self.model = model or self._load()
        self.doc_tokens = self._embed([self._doc(it) for it in items])

    def _load(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(DENSE_MODEL)

    def _doc(self, it):
        return it.topic + " " + it.answer

    def _embed(self, texts):
        embs = self.model.encode(texts, output_value="token_embeddings",
                                 show_progress_bar=False)
        return [_normalize_rows(_to_numpy(e)) for e in embs]

    def _maxsim(self, q, d):
        # q: (nq, dim), d: (nd, dim), both row-normalized. Average of per-query
        # token best matches, so the score sits in a cosine-like range.
        return float((q @ d.T).max(axis=1).mean())

    def search(self, query):
        q = self._embed([query])[0]
        scored = [(it, self._maxsim(q, d)) for it, d in zip(self.items, self.doc_tokens)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored, tokenize(query)

    def answer(self, query):
        return finalize(self, *self.search(query))
