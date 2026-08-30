"""Retrieval strategies behind the grounding contract.

Each index exposes `.search(query) -> (scored, qtokens)` and `.answer(query) ->
Result`. The grounding contract (finalize) is identical across all of them; only
candidate quality differs. LexicalIndex needs no dependencies; DenseIndex and
HybridIndex pull in sentence-transformers + a vector store lazily.
"""
from .lexical import LexicalIndex, SCORE_THRESHOLD
from .dense import DenseIndex, DENSE_MODEL, DENSE_THRESHOLD
from .hybrid import HybridIndex
from .rerank import RerankIndex, RERANK_MODEL, RERANK_THRESHOLD

__all__ = [
    "LexicalIndex", "SCORE_THRESHOLD",
    "DenseIndex", "DENSE_MODEL", "DENSE_THRESHOLD",
    "HybridIndex",
    "RerankIndex", "RERANK_MODEL", "RERANK_THRESHOLD",
]
