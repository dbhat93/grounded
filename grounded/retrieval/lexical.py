"""Lexical retrieval: TF-IDF cosine over the KB.

Fast, dependency-free, and the precision half of the hybrid. It nails proper
nouns and acronyms (Salesforce, SOC 2, Fiserv) that dense models blur, and it
carries the token gate that keeps a single incidental word from answering.
"""
import math

from ..text import tokenize, build_strong_tokens
from ..grounding import finalize

# Below this cosine, refuse. Held at the zero-wrong point on the eval.
SCORE_THRESHOLD = 0.22


class LexicalIndex:
    threshold = SCORE_THRESHOLD
    token_gate = True

    def __init__(self, items):
        self.items = items
        self.strong_tokens = build_strong_tokens(
            [it.topic for it in items] + [it.answer for it in items])
        n = len(items)
        df = {}
        for it in items:
            for tok in set(it.tokens):
                df[tok] = df.get(tok, 0) + 1
        self.idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}
        self.vectors = [self._vec(it.tokens) for it in items]
        self.norms = [math.sqrt(sum(w * w for w in v.values())) for v in self.vectors]

    def _vec(self, tokens):
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        return {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items()}

    def search(self, query):
        qtokens = tokenize(query)
        qvec = self._vec(qtokens)
        qnorm = math.sqrt(sum(w * w for w in qvec.values()))
        scored = []
        if qnorm == 0:
            return scored, qtokens
        for it, vec, norm in zip(self.items, self.vectors, self.norms):
            if norm == 0:
                continue
            dot = sum(w * vec.get(t, 0.0) for t, w in qvec.items())
            if dot:
                scored.append((it, dot / (qnorm * norm)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored, qtokens

    def answer(self, query):
        return finalize(self, *self.search(query))
