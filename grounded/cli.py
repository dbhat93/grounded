"""Command-line entry: `python3 -m grounded [flags] [query]`.

Retrievers:
  (default)     hybrid  (lexical + dense; production)
  --lexical     lexical only  (fast, no model, offline)
  --dense       dense only

Modes:
  <query>       one-shot answer
  (no query)    interactive REPL
  --watch FILE  live entity-triggered surfacing over a transcript (or stdin)
  --eval        run the adversarial guardrail eval
"""
import json
import os
import sys

from .facts import load_kb, EVAL_PATH
from .render import render, render_live
from .text import tokenize


def build_index(mode, routed=False):
    items = load_kb()
    if mode == "lexical":
        from .retrieval import LexicalIndex
        base = LexicalIndex(items)
    elif mode == "dense":
        from .retrieval import DenseIndex
        base = DenseIndex(items)
    elif mode == "rerank":
        from .retrieval import RerankIndex
        base = RerankIndex(items)
    elif mode == "late":
        from .retrieval.late import LateInteractionIndex
        base = LateInteractionIndex(items)
    else:
        from .retrieval import HybridIndex
        base = HybridIndex(items)
    if routed:
        from .structured import RoutedIndex
        return RoutedIndex(items, base)
    return base


def run_once(index, query):
    print(render(index.answer(query)))


def run_interactive(index):
    print("Grounded copilot. Type a question, or Ctrl-C / 'quit' to exit.\n")
    while True:
        try:
            query = input("q> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            return
        print()
        print(render(index.answer(query)))
        print()


def run_watch(index, lines, cooldown=6):
    """Live mode: fire on a known entity in the transcript, then let the grounded
    contract decide whether anything is safe to surface. Silent otherwise."""
    print("Grounded live watch. Fires only on known entities; silent otherwise.\n")
    triggers = index.strong_tokens
    fired = {}
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if not (set(tokenize(line)) & triggers):
            continue
        res = index.answer(line)
        if res.kind != "answer":
            continue
        key = res.items[0].topic_key
        if key in fired and (i - fired[key]) < cooldown:
            continue
        fired[key] = i
        print(render_live(line, res))
        print()


def run_ingest():
    """Run the knowledge/ingestion pipeline over the mocked enterprise sources
    and print a report: provenance, freshness, source-of-truth conflicts, and
    transcript question coverage."""
    from .ingestion import run
    from .ingestion.model import SUPPORTED_FORMATS, SUPPORTED_SOURCES
    from .ingestion.freshness import days_since
    from .ingestion.model import TTL_DAYS
    from .retrieval import LexicalIndex

    report = run()

    # transcript coverage: does the served KB answer the mined buyer questions?
    index = LexicalIndex(load_kb())
    for q in report.questions:
        res = index.answer(q.question)
        q.covered = res.kind == "answer"
        q.answer_id = res.items[0].id if (q.covered and res.items) else None

    print("KNOWLEDGE / INGESTION RUN")
    print("  formats supported: " + ", ".join(sorted(SUPPORTED_FORMATS)))
    print("  sources supported: " + ", ".join(sorted(SUPPORTED_SOURCES))
          + "   (cloud + transcript connectors are MOCK)")

    print("\nDocuments pulled (%d):" % len(report.docs))
    for d in report.docs:
        tag = ("  provider=" + d.provider) if d.provider else ""
        print("  [%-12s] %-28s %-5s  modified %s%s"
              % (d.source_system, d.title[:28], d.fmt, d.source_last_modified, tag))

    print("\nCandidate facts from documents: %d" % len(report.facts))
    for f in report.facts:
        flag = ""
        if f.stale:
            flag = "  [!] STALE %dd (ttl %dd)" % (f.stale_days, TTL_DAYS.get(f.ttl_class, 0))
        print("  %-22s %-14s src=%-12s %s%s"
              % (f.topic_key[:22], "[" + f.status + "]", f.provenance.source_system,
                 f.provenance.locator, flag))

    if report.conflicts:
        print("\nSOURCE-OF-TRUTH CONFLICTS (held for curation): %d" % len(report.conflicts))
        for c in report.conflicts:
            print("  topic '%s' has disagreeing sources:" % c.topic_key)
            for f in c.facts:
                print("     [%s] from %s (%s), verified %s: %s"
                      % (f.status, f.provenance.source_system, f.provenance.doc_title,
                         f.last_verified, f.claim[:70]))

    print("\nAcceptance gate: %d fresh + non-conflicting facts ready to serve, "
          "%d held (stale or conflicting)." % (len(report.accepted()), len(report.held())))

    print("\nTranscripts: %d buyer questions mined (UNVETTED, 0 promoted to facts)."
          % len(report.questions))
    covered = [q for q in report.questions if q.covered]
    gaps = [q for q in report.questions if not q.covered]
    print("  coverage: %d answerable by the KB, %d gaps." % (len(covered), len(gaps)))
    if gaps:
        print("  gaps (questions asked on calls the KB cannot answer):")
        for q in gaps:
            print("     - %-52s (%s / %s)"
                  % (q.question[:52], q.provenance.source_system, q.provenance.locator))
    return 0


def run_promote():
    """Promote accepted ingestion facts into the served KB. Coverage-gated: only
    facts the current KB does not already answer are added (semantic dedup via
    the hybrid index); duplicates are skipped, conflicts and stale facts are
    held. Writes kb/promoted.jsonl, which load_kb then serves."""
    from .ingestion import run
    from .facts import BASE_KB_FILES, PROMOTED_FILE
    from .retrieval import HybridIndex

    report = run()
    accepted = report.accepted()
    index = HybridIndex(load_kb(BASE_KB_FILES))   # dedup against hand-authored only

    from .entities import same_entity
    promoted, skipped, seen = [], [], set()
    for f in sorted(accepted, key=lambda x: x.topic_key):
        if f.topic_key in seen:
            continue
        res = index.answer(f.topic)
        covered = res.kind == "answer"
        if covered:
            cover = res.items[0]
            # entity-aware: a semantic 'covered' is overridden if the candidate
            # names a hard entity the covering fact lacks (ServiceNow vs Salesforce)
            if not same_entity(f.topic, cover.topic + " " + cover.answer):
                covered = False
        if covered:
            skipped.append((f, res.items[0].id))
        else:
            seen.add(f.topic_key)
            promoted.append(f)

    with open(PROMOTED_FILE, "w", encoding="utf-8") as fh:
        for f in promoted:
            fh.write(json.dumps({
                "id": "PROMO-" + f.topic_key,
                "topic_key": f.topic_key,
                "topic": f.topic,
                "claim": f.claim,
                "status": f.status,
                "last_verified": f.last_verified,
                "provenance": {
                    "source_system": f.provenance.source_system,
                    "doc_id": f.provenance.doc_id,
                    "doc_title": f.provenance.doc_title,
                    "locator": f.provenance.locator,
                    "fetched_at": f.provenance.fetched_at,
                },
            }) + "\n")

    print("PROMOTION")
    print("  accepted from ingestion:            %d" % len(accepted))
    print("  promoted (net-new, now served):     %d" % len(promoted))
    for f in promoted:
        print("     + [%s] %-24s from %s (%s)"
              % (f.status, f.topic_key, f.provenance.source_system, f.provenance.locator))
    print("  skipped (already covered by KB):    %d" % len(skipped))
    for f, aid in skipped:
        print("     = %-24s already answered by %s" % (f.topic_key, aid))
    print("  held (conflict/stale, NOT promoted): %d" % len(report.held()))
    print("\n  wrote %s (%d facts); the served KB now includes them."
          % (os.path.basename(PROMOTED_FILE), len(promoted)))
    return 0


def run_live(path=None):
    """Demonstrate speculative two-stage answering over a transcript: an instant
    verbatim/deterministic answer, then a verified (composition-pending) upgrade."""
    from .live import LiveEngine
    from .facts import REPO_ROOT
    index = build_index("lexical", routed=True)      # fast instant stage
    engine = LiveEngine(index)
    path = path or os.path.join(REPO_ROOT, "evals", "sample_call.txt")
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    triggers = index.strong_tokens
    fired = {}
    print("Grounded live: speculative two-stage. Stage 1 instant; stage 2 on dwell "
          "(verified; composition pending).\n")
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or not (set(tokenize(line)) & triggers):
            continue
        r1 = engine.instant(line)
        if r1.kind != "answer":
            continue
        key = r1.items[0].topic_key
        if key in fired and (i - fired[key]) < 6:
            continue
        fired[key] = i
        it = r1.items[0]
        print('  heard: "%s"' % line)
        print("    stage 1 (instant): [%s] %s" % (it.status_label, it.answer[:90]))
        r2 = engine.upgrade(r1, line)
        if r2.kind == "answer":
            print("    stage 2 (dwell):   verified %.2f, composition pending (composer not built)"
                  % getattr(r2, "verify_score", 0.0))
        else:
            print("    stage 2 (dwell):   REFUSED: %s" % r2.note)
        print()
    return 0


def run_verify():
    """Calibrate the faithfulness verifier. Two things must be true before we
    can trust it as a gate: it must not reject known-good answers (false-reject
    ~ 0, so it never causes a miss), and it must reject a claim paired with an
    unrelated source (discrimination, so it will catch an unsupported generated
    claim later). Uses verbatim answers, where the claim is the vetted text."""
    from .verify import Verifier
    from .facts import load_kb
    items = load_kb()
    index = build_index("lexical", routed=True)   # fast; answers are verbatim regardless
    v = Verifier()
    cases = [json.loads(l) for l in open(EVAL_PATH, encoding="utf-8") if l.strip()]

    real_n = real_reject = adv_n = adv_accept = 0
    reject_examples = []
    for i, c in enumerate(cases):
        if c["expect"] == "REFUSE":
            continue
        r = index.answer(c["q"])
        if r.kind != "answer" or not r.items:
            continue
        item = r.items[0]
        claim = item.answer
        # real: the claim against its own source must be supported
        ok, s = v.supports([item.answer], claim)
        real_n += 1
        if not ok:
            real_reject += 1
            reject_examples.append((item.id, s))
        # adversarial: the same claim against an unrelated fact must NOT be supported
        fake = items[(i * 5 + 3) % len(items)]
        if fake.topic_key != item.topic_key:
            ok2, s2 = v.supports([fake.answer], claim)
            adv_n += 1
            if ok2:
                adv_accept += 1

    print("VERIFIER CALIBRATION  (model: nli-deberta-v3-base, threshold %.2f)" % v.threshold)
    print("  real (claim vs its own source), must be SUPPORTED:")
    print("    checked %d, false-rejects %d  (%.0f%% pass)  <- want 100%%"
          % (real_n, real_reject, 100.0 * (real_n - real_reject) / max(real_n, 1)))
    for iid, s in reject_examples:
        print("      false-reject: %s at %.2f" % (iid, s))
    print("  adversarial (claim vs an unrelated source), must be REJECTED:")
    print("    checked %d, false-accepts %d  (%.0f%% rejected)  <- want ~100%%"
          % (adv_n, adv_accept, 100.0 * (adv_n - adv_accept) / max(adv_n, 1)))
    verdict = "TRUSTWORTHY" if (real_reject == 0 and adv_accept <= adv_n * 0.1) else "NEEDS TUNING"
    print("\n  Verdict: %s (no-op over verbatim today; ready as a gate for generation)"
          % verdict)
    return 0


def run_eval(index):
    cases = [json.loads(l) for l in open(EVAL_PATH, encoding="utf-8") if l.strip()]
    correct = refused_ok = miss = wrong = 0
    wrong_rows = []
    for c in cases:
        expect = c["expect"]
        res = index.answer(c["q"])
        got = res.items[0].id if (res.kind == "answer" and res.items) else None
        if expect == "REFUSE":
            if res.kind == "refuse":
                refused_ok += 1
            else:
                wrong += 1
                wrong_rows.append((c["q"], "REFUSE", res.kind, got))
        else:
            if res.kind == "answer" and got == expect:
                correct += 1
            elif res.kind == "refuse":
                miss += 1
            else:
                wrong += 1
                wrong_rows.append((c["q"], expect, res.kind, got))
    print("Eval over %d cases  [%s]" % (len(cases), index.__class__.__name__))
    print("  CORRECT     %2d  (right answer, right row)" % correct)
    print("  REFUSED_OK  %2d  (correctly said 'not in the KB')" % refused_ok)
    print("  MISS        %2d  (refused when it could have answered; safe)" % miss)
    print("  WRONG       %2d  (confident-wrong or answered-when-should-refuse; MUST be 0)" % wrong)
    if wrong_rows:
        print("\n  Confident-wrong cases:")
        for q, exp, kind, got in wrong_rows:
            print("    - %r  expected=%s  got=%s/%s" % (q, exp, kind, got))
    print("\n  Result: %s" % ("PASS (zero wrong)" if wrong == 0 else "FAIL (see above)"))
    return 0 if wrong == 0 else 1


def main(argv):
    mode = "hybrid"
    if "--lexical" in argv:
        argv = [a for a in argv if a != "--lexical"]; mode = "lexical"
    if "--dense" in argv:
        argv = [a for a in argv if a != "--dense"]; mode = "dense"
    if "--rerank" in argv:
        argv = [a for a in argv if a != "--rerank"]; mode = "rerank"
    if "--late" in argv:
        argv = [a for a in argv if a != "--late"]; mode = "late"
    if "--hybrid" in argv:
        argv = [a for a in argv if a != "--hybrid"]; mode = "hybrid"

    if argv and argv[0] == "ingest":
        return run_ingest()
    if argv and argv[0] == "promote":
        return run_promote()
    if argv and argv[0] == "mcp":
        from .mcp_server import main as mcp_main
        return mcp_main()
    if argv and argv[0] == "verify":
        return run_verify()
    if argv and argv[0] == "live":
        return run_live(argv[1] if len(argv) > 1 else None)
    if argv and argv[0] == "meeting-bot":
        from .realtime.meeting_bot import run_meeting_bot_cli
        return run_meeting_bot_cli(argv[1:])

    # deterministic routing is on by default; --no-routed turns it off
    routed = "--no-routed" not in argv
    argv = [a for a in argv if a not in ("--routed", "--no-routed")]

    verify = "--verify" in argv
    if verify:
        argv = [a for a in argv if a != "--verify"]

    watch = "--watch" in argv
    if watch:
        argv = [a for a in argv if a != "--watch"]

    index = build_index(mode, routed=routed)
    if verify:
        from .verify import VerifyingIndex
        index = VerifyingIndex(index)

    if watch:
        if argv:
            with open(argv[0], encoding="utf-8") as fh:
                lines = fh.readlines()
        else:
            lines = sys.stdin
        run_watch(index, lines)
        return 0
    if argv and argv[0] in ("--eval", "-e", "eval"):
        return run_eval(index)
    if argv:
        run_once(index, " ".join(argv))
        return 0
    run_interactive(index)
    return 0
