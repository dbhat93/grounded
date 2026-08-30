"""Dense (semantic) retrieval: sentence embeddings over a vector store.

Closes the synonym and word-form gap lexical cannot ("operating hours" vs
"support hours"). Model chosen by an eval-backed bake-off on 2026-08-07:
thenlper/gte-large won (87 correct / 8-of-12 synonym, zero-wrong at cosine 0.83).
See ARCHITECTURE decision log and the README bake-off table.

Vectors are stored in LanceDB and re-embedded only when the KB text changes.
sentence-transformers and the model download are pulled in lazily.
"""
import hashlib
import os

from ..text import tokenize
from ..facts import KB_DIR
from ..grounding import finalize
from .store import LanceDBStore

DENSE_MODEL = "thenlper/gte-large"
DENSE_THRESHOLD = 0.83   # from the bake-off: max recall at zero-wrong for gte-large
LANCE_DIR = os.path.join(KB_DIR, ".lancedb")
TABLE = "kb_gte_large"


class DenseIndex:
    token_gate = False
    threshold = DENSE_THRESHOLD

    def __init__(self, items, model=None):
        import numpy as np
        self.np = np
        self.items = items
        self.by_id = {it.id: it for it in items}
        self.strong_tokens = set()   # interface parity; not used in dense mode
        self.model = model or self._load_model()
        self.store = LanceDBStore(LANCE_DIR, TABLE)
        self._build_or_open()

    def _load_model(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(DENSE_MODEL)

    def _doc(self, it):
        return it.topic + " " + it.answer

    def _encode(self, texts):
        return self.np.asarray(
            self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype="float32")

    def _build_or_open(self):
        texts = [self._doc(it) for it in self.items]
        key = hashlib.sha1(("\n".join(texts) + "|" + DENSE_MODEL).encode()).hexdigest()
        hashfile = os.path.join(LANCE_DIR, TABLE + ".hash")
        if self.store.has() and os.path.exists(hashfile) and \
                open(hashfile).read().strip() == key:
            self.store.open()
            return
        vecs = self._encode(texts)
        self.store.build([it.id for it in self.items], vecs)
        os.makedirs(LANCE_DIR, exist_ok=True)
        with open(hashfile, "w") as fh:
            fh.write(key)

    def search(self, query):
        qv = self._encode([query])[0]
        hits = self.store.search(qv, k=min(20, len(self.items)))
        scored = [(self.by_id[i], s) for i, s in hits if i in self.by_id]
        return scored, tokenize(query)

    def answer(self, query):
        return finalize(self, *self.search(query))
