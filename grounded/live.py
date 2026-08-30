"""Speculative two-stage live answering (scaffold).

Stage 1: an instant, deterministic/verbatim answer on the hot path (sub-second).
Stage 2 (on dwell): a composed-and-verified answer that silently replaces it.

Composition (the LLM composer) is deliberately not built yet. It is sequenced
after the verifier and gated on the egress decision, so stage 2 here runs the
faithfulness verifier over the answer and marks it verified, with the composer
as an explicit stub. The shape and the verifier wiring are in place: the composer
drops into stage 2 behind the same gate, and an unverified composition is refused
before it ever reaches the buyer.
"""
from .grounding import Result


class LiveEngine:
    def __init__(self, base, verifier=None):
        self.base = base                     # a routed index (deterministic-first)
        self.verifier = verifier             # loaded lazily on first upgrade

    def instant(self, question):
        """Stage 1: fast, verbatim/deterministic. This is what the rep sees now."""
        return self.base.answer(question)

    def upgrade(self, result, question):
        """Stage 2: compose (STUB today), then verify before surfacing. Silently
        replaces stage 1 if the rep lingers on the answer."""
        if result.kind != "answer" or not result.items:
            return result
        if self.verifier is None:
            from .verify import Verifier
            self.verifier = Verifier()
        item = result.items[0]
        # STUB: the real composer would paraphrase/synthesize over the retrieved
        # facts here. Until it exists, the composed text is the vetted text.
        composed = item.answer
        ok, score = self.verifier.supports([item.answer], composed)
        if not ok:
            return Result("refuse", items=result.items, scores=result.scores,
                          qtokens=result.qtokens,
                          note="composed answer failed verification (%.2f)" % score)
        result.verify_score = score
        result.composed = composed
        result.composition_pending = True    # marker: real composer not yet built
        return result
