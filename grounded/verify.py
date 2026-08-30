"""Faithfulness verifier: does a claim actually follow from its cited source?

This is the run-time twin of the eval gate. Today it is a deliberate no-op over
verbatim answers (the claim IS the source text), and that is the point: we
install it now and calibrate its false-reject rate on known-good content, so it
is already trusted the day composition is turned on and claims are generated
rather than quoted. On that day, the claim is the generated sentence and the
sources are the retrieved passages; a claim that does not entail from a source
is vetoed here, before it ever reaches the buyer.

Default is a local NLI cross-encoder (no egress). Swappable for a MiniCheck-class
faithfulness model or a hosted checker once the egress question is answered.
"""
import numpy as np

from .grounding import Result

VERIFY_MODEL = "cross-encoder/nli-deberta-v3-base"
SUPPORT_THRESHOLD = 0.5


def _softmax(x):
    x = np.asarray(x, dtype="float64")
    e = np.exp(x - x.max())
    return e / e.sum()


class Verifier:
    def __init__(self, model=None, threshold=SUPPORT_THRESHOLD):
        self.threshold = threshold
        self.model = model or self._load()
        # NLI label order varies by checkpoint; detect the entailment index by
        # scoring an identical premise/hypothesis (which must entail).
        self.entail_idx = self._detect_entail_idx()

    def _load(self):
        from sentence_transformers import CrossEncoder
        return CrossEncoder(VERIFY_MODEL)

    def _detect_entail_idx(self):
        s = "The integration is generally available today."
        logits = np.asarray(self.model.predict([(s, s)]))
        return int(np.argmax(logits[0]))

    def entailment(self, source, claim):
        """P(source entails claim)."""
        logits = np.asarray(self.model.predict([(source, claim)]))
        return float(_softmax(logits[0])[self.entail_idx])

    def supports(self, sources, claim):
        """Is the claim supported by its best-matching source?"""
        best = 0.0
        for s in sources:
            best = max(best, self.entailment(s, claim))
        return best >= self.threshold, best


class VerifyingIndex:
    """Wrap a base retriever with the run-time faithfulness gate. Verbatim
    answers pass trivially (claim == source); when composition is added, the
    claim becomes the generated text and an unsupported claim is refused here."""

    def __init__(self, base, verifier=None):
        self.base = base
        self.verifier = verifier or Verifier()
        self.strong_tokens = getattr(base, "strong_tokens", set())

    def answer(self, query):
        r = self.base.answer(query)
        if r.kind != "answer" or not r.items:
            return r
        item = r.items[0]
        claim = item.answer                 # today the claim is the vetted text
        sources = [item.answer]             # cited against its own source
        ok, score = self.verifier.supports(sources, claim)
        r.verify_score = score
        if not ok:
            return Result("refuse", items=r.items, scores=r.scores, qtokens=r.qtokens,
                          note="failed faithfulness check (%.2f): claim not supported "
                               "by its source" % score)
        return r
