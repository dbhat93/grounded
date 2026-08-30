# Grounded: Architecture

Living document. As of 2026-08-07. Clean-room (no prior-employer data, knowledge, or code).

This is the anchor for a production build. It states the one invariant, separates the guarantee from the mechanism, defines the data model, lays out the stack and the build order, and lists the decisions still open. Every later choice should trace back to something here. If a change contradicts this doc, update the doc in the same change.

---

## 0. Posture

Grounded is a real product and, eventually, a real company. Not a demo. The stdlib lexical prototype in this repo was a proving ground; its job was to show that "never wrong out loud" is achievable and testable under adversarial pressure, and that job is done (118-case adversarial eval, zero confident-wrong). From here the work is production-grade, and every foundational decision is treated as something that compounds.

---

## 1. The invariant

**Never wrong out loud.** Formally: for any question, the system emits exactly one of

1. a **vetted claim** that traces to a cited source, carries a live-vs-roadmap label, and carries a freshness signal, or
2. an **explicit refusal** ("not in the knowledge base, follow up in writing").

It never emits an unverified claim as fact. Everything else in this document is mechanism and may change. This one rule may not.

Corollaries, load-bearing:

- The **refusal decision is deterministic and is never delegated to a generative model.** The model is never asked "do you know this." That question is answered by retrieval score and freshness, in code.
- A wrong-out-loud event in production is a **Sev-1**, and the case that produced it becomes a permanent eval fixture.
- The eval harness's `WRONG` count is the **release gate**. It must be 0 to ship.

---

## 2. Separation of guarantee and mechanism

Four layers, one direction of trust:

```
Retrieval  ->  Grounding contract  ->  Composition (optional)  ->  Surface
(recall)       (the gate: labels,       (constrained phrasing)      (live / async /
               refusal, guards)                                      prep / review)
```

The guarantee lives entirely in the **grounding contract** layer. Retrievers and models are swappable behind it. This is why we can move from lexical to hybrid to a better embedder without touching the promise: the gate is the same, only the candidate quality changes.

---

## 3. The fact model

Every unit of knowledge is a **Fact**, and provenance and freshness are columns, not afterthoughts.

| field | meaning |
|---|---|
| `id` | stable identifier |
| `topic_key` | canonical topic; twins across sources share it (dedup, negative-knowledge linking) |
| `topic` | the question or entity the fact is about (what drives retrieval) |
| `claim` | the vetted answer text, returned verbatim by default |
| `status` | `GA` / `Beta` / `Roadmap` / `Not supported` / `Battle card` |
| `source` | system of record + a locator (doc id, row, URL) |
| `last_verified` | date the claim was last confirmed true |
| `ttl_class` | how fast this kind of claim decays (see freshness) |
| `verified_by` | human or rule that vetted it |
| `tenant` | owning customer (multi-tenant isolation) |
| `tags` | product area, vertical, etc. |

**Negative knowledge is first-class.** "We do not support Fiserv Premier" is a Fact with `status: Not supported`, not an absence. This is what turns a dangerous near-miss into a definitive, correct answer.

---

## 4. Retrieval (recall, not the guarantee)

Production retrieval is **hybrid**, because we have direct evidence (2026-08-07 bake-off, recorded in README) that no single method is both safe and complete:

- **Lexical** (BM25 / exact) nails proper nouns, acronyms, and product and competitor names. A small dense model ranked the correct "Salesforce" row third and mis-ranked others.
- **Dense** (a strong embedding model) closes the synonym and word-form gap ("operating hours" ~ "support hours") that lexical cannot.
- Neither alone is acceptable: dense-only produced a compliance confident-wrong ("money laundering" -> check fraud) that no threshold could separate from correct answers.

Pipeline: lexical candidates `union` dense candidates -> **cross-encoder reranker** -> top-k. The reranker earns its place on the sibling-cluster problem (Fiserv DNA sitting next to the Fiserv Premier negative fact); a strong reranker resolves what a bi-encoder blurs.

Store: a real vector store (pgvector, LanceDB, or Qdrant; decision open). Embeddings are precomputed and cached; only the query is embedded at request time.

---

## 5. The grounding contract (the gate)

Deterministic. No LLM. Input: the query plus ranked candidates. Output: one vetted fact with label, citation, and freshness, or a structured refusal with a reason. Steps, in order:

1. **Twin-collapse.** Merge candidates sharing a `topic_key` so one fact is one result.
2. **Confidence threshold.** Below the bar, refuse. This is the no-LLM "I don't know."
3. **Near-miss guards.** Number/version mismatch (a question pinning "SOC 1" must not answer from a SOC 2 fact). Brand variants are handled by curated negative facts, not a heuristic.
4. **Ambiguity.** A near-tie is broken by which fact the question lexically names (topic tokens). A genuine coin-flip refuses.
5. **Freshness.** If the best fact is older than its `ttl_class` allows for a spoken claim, flag it or refuse depending on claim type. A fresh-looking wrong answer is worse than none.
6. **Emit.** The vetted fact, its `status` label, its citation, its freshness, or a refusal.

This module is the product. It is small, hardened, and exhaustively tested. It is the thing a competitor bolting "grounded mode" onto a volume tool cannot retrofit cheaply.

---

## 6. Composition (optional, constrained)

Composition exists only to improve phrasing or synthesize across a few facts, and it runs **only on facts that already passed the gate**. The contract to the model is strict: compose only from these facts, cite each, preserve the labels, and if they do not answer the question say not-in-bank. A **claim-verification pass** then checks that every concrete assertion in the output traces to a provided fact; on failure the system drops to the verbatim fact or refuses.

Default is verbatim (zero hallucination). Composition is an opt-in dial, turned on where natural phrasing is worth a managed, verified risk. The model is never in the refusal path.

---

## 7. Knowledge and ingestion (the hard, defensible half)

The value is only as good as the curated, current knowledge behind it. This layer is where trust is actually engineered, and it is the unglamorous work competitors avoid.

- **Sources.** Drive, Notion, Slack, sheets, internal sites. Connect, extract, normalize into Fact records.
- **Provenance.** Every Fact carries its source and locator and the time it was retrieved. Nothing enters the index unattributed.
- **Freshness gates.** Each Fact has a `last_verified` and a `ttl_class`. Security posture, pricing, and GA status decay at different rates. Stale facts are flagged or auto-suppressed, never silently served as fresh.
- **Source-of-truth conflict detection.** When two sources disagree on the same `topic_key`, the system flags it for curation instead of silently choosing. (This is the exact failure a real sales-knowledge base hits: the same battle card in Drive, a wiki, Slack, and a scraper, all subtly different.)
- **Curation workflow.** A cheap review surface: approve, re-confirm, mark stale. Provenance always visible.

This layer, plus the eval harness, is the moat.

---

## 8. Eval as CI (the release gate)

The adversarial eval suite (118 cases today) is production infrastructure, not a script.

- Scoring: `correct` / `refused-ok` / `miss` (refused when it could have answered; safe) / `WRONG` (confident-wrong, or answered when it should refuse).
- **Gate: `WRONG` must be 0 to merge or release.** CI fails otherwise.
- The suite grows adversarially. Every real wrong or near-miss seen in production becomes a permanent fixture. It only ratchets tighter.
- `refusal-rate` and `miss-rate` are tracked as product-health metrics. Too-high refusal is a recall problem to fix in retrieval, not a safety problem.
- Runs are per-retriever and per-model, so swapping an embedder or a reranker is a decision backed by numbers, not vibes.

---

## 9. Real-time service

The live-call form factor. Transcript in (local ASR / Whisper), grounded card out, glance-able, on a screen the prospect cannot see. The human speaks; the copilot assists.

- **Trigger.** Entity-triggered by default (high precision: fire when a known product, integration, acronym, or competitor is named), with optional question-detection to widen. The entity mention only *starts* the lookup; the grounding contract still decides whether anything is safe to surface. Silence when nothing is vetted.
- **Latency budget.** End to end under ~5-10s; retrieval hot path under ~1s. Nothing slow (no dependency on a general answer engine or a chain of remote calls) sits in the hot path. This is a hard constraint, not a target.
- Productionize the `--watch` prototype as a streaming service with per-session state and per-topic cooldowns.

---

## 10. Surfaces (the suite, phased)

One grounded core, many surfaces. Phase them; do not build the suite before the core is trusted.

1. Live and async copilot (the wedge).
2. Pre-engagement research and prep briefs.
3. Exec and revenue-review synthesis.
4. Post-call scoring and coaching.

---

## 11. Security, tenancy, compliance

Selling to regulated buyers means holding ourselves to their bar.

- **Multi-tenant isolation.** Per-tenant knowledge base and vector namespace. No cross-tenant retrieval, ever.
- **Audit.** Every surfaced claim is logged with its source, label, and confidence. That log is a defensible record for a regulated buyer and a feed for the eval suite.
- RBAC, encryption at rest and in transit, secret management.
- Our own SOC 2 is on the roadmap. We sell trust; we carry the attestation.

---

## 12. Observability

Production metrics: `wrong-rate` (target 0, alarmed), `refusal-rate`, freshness distribution, latency p95, retrieval hit-rate. Every surfaced claim is logged with source and confidence, for audit and for growing the eval set.

---

## 13. Clean-room governance

Blank repo. No prior-employer data, knowledge base, or code, in either direction. All testbed data is fictional (the Kestrel fraud/KYC company). The provenance of the codebase itself is an asset: keep it clean so it is never in question. Founder equity papered before the real build.

---

## 14. Target repo structure (restructure in place)

Evolve this repo; keep the KB and eval assets and the git history. Migrate the single-file `grounded.py` into modules:

```
grounded/
  facts.py          Fact model + loaders (KB today, DB later)
  retrieval/        lexical.py, dense.py, hybrid.py, rerank.py
  grounding.py      the contract (threshold, guards, labels, refusal)  <- the product
  compose.py        constrained composition + claim verification
  freshness.py      ttl classes, staleness policy
  realtime/         transcript ingest, triggering, streaming surface
  api/              service endpoints
ingestion/          source connectors, provenance, conflict detection
kb/                 fictional Kestrel data (today) -> per-tenant store (later)
evals/              adversarial suite + runner (CI gate)
tests/              unit tests for the contract and guards
ARCHITECTURE.md     this file
README.md
```

---

## 15. Build order

- **Phase 0 (done).** Lexical MVP, adversarial eval, grounding contract proven, entity-trigger prototype, embeddings bake-off with a recorded finding.
- **Phase 1.** Restructure in place. Retrieval to production hybrid (lexical + strong dense + reranker) over a real vector store. Wire the eval as a CI gate.
- **Phase 2.** Knowledge and ingestion layer: provenance, freshness gates, conflict detection, curation surface.
- **Phase 3.** Constrained composition + claim verification, behind a flag, verbatim as default.
- **Phase 4.** Real-time service; live and async copilot surfaces.
- **Phase 5.** Multi-tenant, security, own SOC 2; expand into the suite.

---

## 16. Non-goals (for now)

No autonomous agent running the demo. Nothing that speaks directly to the customer. No generic horizontal roleplay. No rip-and-replace of the CRM. We assist a human in a high-trust room; that is the whole scope until the core is trusted.

---

## 17. Open decisions

Each of these should be resolved with the eval harness, not by preference.

- **Vector store:** pgvector vs Qdrant vs LanceDB.
- **Embedding model:** local (bge-large, e5-large) vs API (text-embedding-3-large) vs a retrieval-tuned vendor (Voyage, Cohere). Decide with an eval-backed bake-off; the small MiniLM is already ruled out.
- **Reranker:** Cohere Rerank vs a local cross-encoder.
- ~~**Compose-by-default vs verbatim-by-default.**~~ RESOLVED 2026-08-07: verbatim on the live hot path; composition is coming, arriving via a verifier-gated speculative upgrade (see decision log).
- **Freshness TTLs by claim class** (security, pricing, GA status).
- **First vertical and its data-residency posture.** PARTIAL 2026-08-07: data-residency (egress) is unknown and being validated with a real buyer within weeks; build model-agnostic (local vs hosted swappable) until then.
- **Capture audio egress:** cloud meeting bot (chosen) sends call audio to our cloud; a no-egress buyer forces local ASR. Keep capture behind an interface.
- **Verifier model** for the faithfulness gate (MiniCheck-class / NLI / AlignScore), local vs hosted, pending the egress answer.

---

## 18. Decision log

- **2026-08-07.** Confirmed production posture and a real-company goal. Chose architecture-doc-first and restructure-in-place. Recorded the embeddings finding (small dense model underperforms and is unsafe if recall-tuned; hybrid + reranker is the path). Adopted entity-triggered surfacing (the one reusable idea from a sibling internal build) on top of the grounded contract.
- **2026-08-07 (bake-off).** Ran an eval-backed embedding bake-off (6 models, metric = max correct at WRONG=0, threshold swept, same grounding contract). Results (correct / synonym-of-12): lexical 84/3; MiniLM-L6 77/4; bge-small 82/4; bge-base 85/5; bge-large 86/7; e5-large 84/5; **gte-large 87/8 (chosen)**. bge-large is the backup. Confirmed the earlier "embeddings underperform" result was a model problem, not architecture: MiniLM was worst. Even the best dense-alone is only +3 over lexical, which is the empirical case for hybrid (dense still misses proper nouns lexical nails). **Vector store: LanceDB for the build (embedded, real ANN, no server), behind a `VectorStore` interface, with pgvector as the production target.**
- **2026-08-07 (Phase 1 done).** Restructured the single file into the `grounded/` package (text, facts, grounding, render, retrieval/{lexical,dense,store,hybrid}, cli). Entry is now `python3 -m grounded`. Rebuilt retrieval as production hybrid: dense = gte-large over LanceDB; hybrid = a late-fusion ensemble that runs the lexical and dense pipelines each through the full contract and combines verdicts (either confident answer wins; two-answer disagreement broken by topic-name anchor; both-refuse refuses). Eval, per retriever, zero-wrong: lexical 84, dense 87, **hybrid 89** correct of 93 answerable. Union recall confirmed; zero-wrong preserved because each pipeline is individually tuned to zero-wrong.
- **2026-08-07 (reranker evaluated, not adopted as default).** Built a cross-encoder rerank stage (`retrieval/rerank.py`): union candidate generation (lexical top-12 + dense top-12) then a cross-encoder, sigmoid to [0,1], same grounding contract. Bake-off (max correct at WRONG=0, threshold swept): ms-marco-MiniLM 78, bge-reranker-base 81, bge-reranker-large 82, all BELOW the hybrid ensemble's 89. Reason: one reranked list + one threshold cannot match the ensemble's two independently calibrated shots, and MS-MARCO-trained rerankers are not calibrated for a small, terse fact KB (rerankers help most on large, passage-like candidate sets). Kept behind an experimental `--rerank` flag (bge-reranker-large, threshold 0.51) to re-evaluate as the corpus grows. Ensemble remains the default. The eval rejected the technique; that is the discipline working.
- **2026-08-07 (Phase 2 started: knowledge/ingestion, mock docs only).** Built `grounded/ingestion/` and `python3 -m grounded ingest`. Formats XLSX/PDF/DOCX extracted for real (openpyxl/pypdf/python-docx) over `fixtures/`; cloud connectors (Google Drive, SharePoint, Office 365) and transcript/call-intel connectors (Gong, Otter, Granola, Zoom, Sybill, Wispr, Minutes) are MOCK (declare support, return fixtures, no auth). Pipeline: connectors -> RawDoc -> extract -> factify (candidate facts with provenance + freshness class) -> freshness pass -> conflict detection. Every fact carries source system + doc + exact locator. TTLs by claim class. **Source-of-truth conflict detection works** (seeded EU-residency conflict: Google Sheet Roadmap vs SharePoint GA, held for curation). **Trust boundary enforced**: transcripts are untrusted, never promoted to facts; mined only for buyer questions, then checked for KB coverage/gaps (found 3 real gaps).
- **2026-08-07 (structured / deterministic layer + question routing).** Built `grounded/structured.py` and `python3 -m grounded --routed`. Some questions have exactly one correct value; the router sends those to an exact lookup against a structured triple `(entity, status, GA|Beta|Roadmap|Not-supported)` derived from the KB, and defers everything else to the probabilistic (retrieval) base. Safety gates: fires only on an availability-intent question that names a single entity uniquely (ambiguous entity defers), and runs the number/version guard (so "SOC 1" cannot resolve the SOC 2 triple). Answers are marked "exact (deterministic status lookup)", not a similarity score. Evals held zero-wrong on both bases (routed+lexical 84, routed+hybrid 89); the score is unchanged because those cases were already correct, but the availability answers are now deterministic rather than threshold-passing similarity, which hardens the never-present-roadmap-as-live promise to a certainty. This is the extractive/deterministic end of the retrieval spectrum (CONCEPT architecture section) made concrete. The triple = knowledge-graph (subject, predicate, object); the KB's `status` field was already one.
- **2026-08-07 (value triples + routing is now default).** Extended the structured layer with **value triples** (uptime SLA, scoring latency, retention period, implementation time, support hours), each citing the KB fact that holds the value and addressed by distinctive trigger tokens; a value question ("what is your uptime SLA?") routes to exact lookup, unique-trigger-only, number-guarded. Made deterministic routing the **default** (`--no-routed` disables). Zero-wrong on both bases; on the lexical base value routing recovered a synonym miss (84 -> 85: "operating hours" resolves deterministically via the "hour" trigger with no embedding model), routed+hybrid stays 89. Every command is now deterministic-first: exact lookup for status/value questions, probabilistic retrieval for the rest.
- **2026-08-07 (promotion: ingestion feeds retrieval).** `python3 -m grounded promote` closes the loop. Accepted facts (fresh, non-conflicting) are **coverage-gated** against the hand-authored KB via the hybrid index: only facts the KB does not already answer are written to `kb/promoted.jsonl` (served alongside the hand KB); duplicates are skipped, conflicts/stale held. Run: 16 accepted, 15 skipped as already-covered (semantic dedup correctly caught near-duplicates like "Encryption" vs the existing encrypted-at-rest fact), 1 net-new promoted (`databrick-export` from the mocked Google Sheet). Before: "do you export to databricks?" refused; after: answers GA with a citation carrying full provenance to `Capabilities!row9`. Both evals held zero-wrong (lexical 84, hybrid 89). **Finding:** semantic dedup false-positived on a sibling entity ("ServiceNow case sync" matched the Salesforce case-sync fact and was skipped), which also exposed a latent base-KB near-miss (a ServiceNow question answers Salesforce). Entity-aware dedup and curated negative facts for sibling integrations are a curation-layer task; a quick heuristic misfires the other way (would falsely promote "encryption" vs "encrypted"). Logged, not hacked.
- **2026-08-07 16:59 PDT (product-direction decisions, from the architecture-review grill).** Set the next-phase direction by forcing eight decisions. Going forward, decisions carry a time, not just a date.
  - *Vetted core size:* **Large** (tens of thousands of facts per customer). Long-context-over-the-whole-core is off the table; retrieval quality matters a lot.
  - *Fact mix:* **Even split** structured vs prose. Equal investment in the typed-fact/graph layer and in strong retrieval for the prose tail.
  - *Generation:* **Composition is coming** (not verbatim-forever). Therefore the **verifier is the #1 build**, before generation is ever turned on.
  - *First user/surface:* **Live in-call copilot** (highest wow, highest adoption + infra risk).
  - *Live answer production:* **Speculative two-stage.** Instant verbatim/deterministic answer on the hot path; a silent upgrade to a composed-and-verified answer if the rep lingers. The live path needs both layers wired to swap in place.
  - *Call audio capture:* **Cloud meeting bot** (ASR in our cloud). This is audio egress and bets the beachhead buyer allows it. Keep capture behind an interface so local ASR can swap in for a no-egress buyer.
  - *Egress:* **Unknown, resolving soon.** Validate with a real regulated buyer within weeks; until then everything model-facing (embeddings, generation, verification, ASR) stays swappable local vs hosted.
  - Confirmed modern adoptions (the "right steps now"): a **fast faithfulness/entailment verifier** as a stage in `finalize`, built now while it is a no-op over verbatim answers so its false-reject rate is calibrated on known-good content before composition arrives; a **typed-fact / entity-resolved store** as primary for the structured half (entity resolution fixes the ServiceNow-vs-Salesforce dedup); **late-interaction retrieval (ColBERT), and ColPali for documents/decks** behind the existing retriever interface for the prose half at scale.
  - Explicitly avoided: agents in the live hot path (latency + hallucination surface); LLM-judge as the release gate (the deterministic zero-wrong gate stays the hard gate; LLM-judge is a non-gating signal only); a framework as the core control flow (the owned, thin grounding contract is the IP); model-size chasing (invest in the verifier and knowledge quality, not a bigger generator).
  - Tension to watch: cloud-bot capture conflicts with a no-egress buyer; it is gated on the egress validation above.
  - **Build order:** (1) the verifier seam, (2) typed-fact/entity store + entity resolution, (3) ColBERT behind the retriever interface, (4) live surface (speculative two-stage), gated on the egress answer for the audio path. Dhiraj returns later to build; the verifier is first.
- **2026-08-09 19:16 PDT (steps 2-4 built + QA sprint).** Build order steps 2, 3, 4.
  - *Step 2, entity resolution* (`grounded/entities.py`): `hard_entities` extracts ALLCAPS acronyms + CamelCase brands (ServiceNow, SOC, FedRAMP), which name a specific thing, unlike a common capitalized word (Encryption). Promotion dedup now overrides a semantic "covered" verdict when the candidate names a hard entity the covering fact lacks. Fixes the logged ServiceNow-vs-Salesforce false-positive: promote now yields **2 net-new (databricks + servicenow)**, still skipping the 14 real duplicates (including "encryption").
  - *Step 3, late-interaction retrieval* (`grounded/retrieval/late.py`, `--late`): per-token vectors + MaxSim, using the gte model's token embeddings (a ColBERT-trained checkpoint is a drop-in swap). Best zero-wrong threshold 0.81 -> 87 correct, ties dense, does not beat hybrid (89) on this 150-fact corpus, same lesson as the reranker: fancier retrieval pays off at large corpus scale, not here. Real and behind the interface for that day. (Bug found + fixed in QA: token embeddings returned as MPS tensors, needed `.cpu()`.)
  - *Step 4, speculative two-stage live* (`grounded/live.py`, `live` command): stage 1 instant deterministic/verbatim; stage 2 on dwell runs the verifier and (STUB) composes, marking "composition pending". The composer is deliberately not built (sequenced after the verifier, gated on egress); the shape and the verifier wiring are in place. Demo verified 0.99-1.00 over verbatim, as expected.
  - *QA sprint:* full eval matrix (lexical 84, dense 87, hybrid 89, routed+lexical 85, routed+hybrid 89) all **zero-wrong** on the post-promotion KB; late sweep; live demo. Result: all retrievers zero-wrong.
- **2026-08-13 13:42 PDT (MCP server: Grounded is callable by any agent).** Built `grounded/mcp_server.py` on the official MCP Python SDK (`mcp` 2.0.0, `MCPServer` high-level API; note FastMCP was renamed/relocated to `MCPServer` in 2.0). Exposes one tool, `grounded_answer(question) -> dict`, which returns a vetted, cited, live-vs-roadmap-labeled answer or an explicit refusal, preserving the full cite-or-refuse contract: an agent that calls it cannot be led into a confident wrong answer because the tool will not produce one. Default retriever routed+lexical (instant start, no model, no egress; `GROUNDED_MCP_MODE=hybrid` for semantic). Run `python -m grounded.mcp_server` or `python -m grounded mcp` (stdio). Smoke-tested: Fiserv DNA->GA/cite, Temenos T24->ROADMAP, Fiserv Premier->NOT SUPPORTED, SOC 3->REFUSED (number guard), SAP->REFUSED; server starts clean over stdio. Chosen over the third-party agent directories reviewed earlier (`aiagenta2z/mcp-marketplace`, PyPI `ai-agent-framework`), which were rejected as unvettable deps. This is the "compatible AF" win: the never-wrong guarantee now travels with the tool call into any MCP client (Claude Desktop, IDEs, other agents). Next for it: list in the official MCP registry.
- Also shipped 2026-08-09: **public web demo** (`demo/index.html`, an Artifact) with the lexical grounding engine ported to in-browser JS over fictional Kestrel data (watch-it-refuse, no CLI). And the **feature-vs-company validation kit** (`discovery/`).
- **2026-08-09 18:58 PDT (verifier built, step 1 of the build order).** Built `grounded/verify.py`: a faithfulness gate (`Verifier` + `VerifyingIndex`) that checks whether an answer's claim is entailed by its cited source, using a local NLI cross-encoder (`cross-encoder/nli-deberta-v3-base`, egress-safe, swappable for a MiniCheck-class model). Wired as `--verify` (wraps any retriever) and a `verify` calibration command. Installed as a deliberate **no-op over today's verbatim answers** (claim == source). Calibration (`python3 -m grounded verify`): over 85 real (claim vs its own source) pairs, **0 false-rejects (100% pass)** so it never causes a miss; over 84 adversarial (claim vs an unrelated source) pairs, **94% correctly rejected** (5 false-accepts, generic answers like "Yes. Generally available." weakly entail many sources). Verdict: trustworthy. The point of building it now: it is calibrated on known-good content and proven not to reject vetted answers, so it is already trusted the day composition is turned on and claims are generated rather than quoted. Threshold/model tuning (raise 0.5, or swap to MiniCheck) happens then, against real generated claims. **Env note:** must run with `/Users/dhirajbhat/.pyenv/versions/3.11.10/bin/python` (deps live there); bare `python3` may hit Homebrew 3.14 with no deps.
