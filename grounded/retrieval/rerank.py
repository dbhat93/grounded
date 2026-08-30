"""Reranked retrieval: union candidate generation, then a cross-encoder.

Two-stage, and the cleanest expression of the hybrid idea:

  1. Candidate generation for recall: the union of lexical top-N and dense
     top-N. Either arm can surface the right fact.
  2. Precision: a cross-encoder scores each (query, candidate) pair jointly
     (far sharper than bi-encoder cosine, which is what tightens sibling cases
     like Fiserv DNA vs Fiserv Premier).

The reranked scores (sigmoid to [0,1]) then feed the same grounding contract as
every other retriever.

STATUS: experimental. An eval-backed bake-off (2026-08-07) found that a rerank
stage UNDERPERFORMS the hybrid ensemble at zero-wrong on this KB: ms-marco 78,
bge-reranker-base 81, bge-reranker-large 82, versus the ensemble's 89. A single
reranked list plus one threshold cannot match the ensemble's two independently
calibrated shots, and MS-MARCO-trained rerankers are not calibrated for a small,
terse fact KB. Kept behind `--rerank` to re-evaluate as the corpus grows (where
rerankers help most). The ensemble stays the default. See ARCHITECTURE.
"""
import math

from ..text import tokenize
from ..grounding import finalize
from .lexical import LexicalIndex
from .dense import DenseIndex

RERANK_MODEL = "BAAI/bge-reranker-large"   # best of the three baked off
RERANK_THRESHOLD = 0.51                      # its zero-wrong point on the eval
POOL_PER_ARM = 12                            # candidates taken from each retriever


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


class RerankIndex:
    token_gate = False
    threshold = RERANK_THRESHOLD

    def __init__(self, items, model=None, cross=None):
        self.items = items
        self.lexical = LexicalIndex(items)
        self.dense = DenseIndex(items, model=model)
        self.cross = cross or self._load_cross()
        self.strong_tokens = self.lexical.strong_tokens   # for live watch triggers

    def _load_cross(self):
        from sentence_transformers import CrossEncoder
        return CrossEncoder(RERANK_MODEL, max_length=512)

    def _pool(self, query):
        ls, _ = self.lexical.search(query)
        ds, _ = self.dense.search(query)
        seen, pool = set(), []
        for it, _ in list(ls[:POOL_PER_ARM]) + list(ds[:POOL_PER_ARM]):
            if it.id not in seen:
                seen.add(it.id)
                pool.append(it)
        return pool

    def search(self, query):
        pool = self._pool(query)
        if not pool:
            return [], tokenize(query)
        raw = self.cross.predict([(query, it.topic + " " + it.answer) for it in pool],
                                 show_progress_bar=False)
        scored = sorted(zip(pool, (_sigmoid(float(s)) for s in raw)),
                        key=lambda x: x[1], reverse=True)
        return scored, tokenize(query)

    def answer(self, query):
        return finalize(self, *self.search(query))
