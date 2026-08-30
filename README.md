# Grounded

<!-- mcp-name: io.github.dbhat93/grounded -->

A trust-first answer layer for high-trust sales. **Cite the source or say "I don't know." Never confidently wrong.**

**[Try the live demo](https://claude.ai/code/artifact/264893fb-f350-4354-ab61-9d75cf3076b6):** type a hard sales question and watch it answer with a citation, label GA vs roadmap, or refuse to guess.

See [CONCEPT.md](CONCEPT.md) for the thesis and market read, and [ARCHITECTURE.md](ARCHITECTURE.md) for the production design. This repo is the working core of the wedge: a grounded copilot.

## What this is

Type a product / integration / security question, get back **one vetted answer** with a citation and a live-vs-roadmap label, **or** a refusal ("not in the knowledge base"). It runs against a fictional testbed company (**Kestrel**, a made-up fraud/KYC SaaS selling into banks) so there is zero proprietary data anywhere in the repo.

The core design decision: the answer returned **is the vetted fact, verbatim**. Nothing is composed or paraphrased by a model, so it structurally **cannot hallucinate**. Grounding is the whole product; a constrained LLM composition layer is a later, optional dial (see ARCHITECTURE).

## Run it

```bash
python3 -m grounded "do you integrate with fiserv dna?"    # one-shot (hybrid, default)
python3 -m grounded --lexical "..."                        # lexical only (fast, no model)
python3 -m grounded --eval                                 # guardrail eval (hybrid)
python3 -m grounded --lexical --eval                       # guardrail eval (lexical)
python3 -m grounded --watch evals/sample_call.txt          # live entity-triggered mode
python3 -m grounded                                        # interactive REPL
```

Retrievers: **hybrid** (default; lexical + dense, production), **`--lexical`** (stdlib, deterministic, no dependencies, offline), **`--dense`** (semantic only), **`--rerank`** (experimental; adds a cross-encoder, currently underperforms the ensemble, see below). Hybrid and dense need `sentence-transformers`, `lancedb`, and a one-time model download (`thenlper/gte-large`); the KB vectors are then cached in an on-disk LanceDB store.

## The guardrail

`evals/eval_set.jsonl` is 118 adversarial questions built to attack the "never wrong" promise: answerable paraphrases (GA), synonym/word-form paraphrases ("operating hours" for support hours), beta/roadmap traps phrased as if live, honest-no, off-domain, leading absolute-claim traps ("guarantee 100% of fraud"), standard/version variants ("SOC 1" vs SOC 2), and near-miss brand variants ("Fiserv Premier" vs Fiserv DNA). The harness scores each as:

- **CORRECT** right answer, right row
- **REFUSED_OK** correctly said "not in the KB"
- **MISS** refused when it could have answered (safe, not harmful)
- **WRONG** confident-wrong, or answered when it should have refused

**`WRONG` must be 0.** `--eval` exits non-zero if it is not. This is the release gate. Current results by retriever (93 answerable of 118):

| retriever | correct | miss | wrong |
|---|---|---|---|
| lexical | 84 | 9 | 0 |
| dense (gte-large) | 87 | 6 | 0 |
| **hybrid (default)** | **89** | **4** | **0** |

## How grounding is enforced

1. **Retrieval, not generation.** The vetted row is the answer.
2. **Refuse below a confidence threshold.** No match, no answer.
3. **Shared-token gate.** A match built on one incidental word ("policy", "fraud") is rejected. A single shared token answers only when it is a proper-noun/acronym the buyer named (Salesforce, SAML, detected by case in the source), or when the whole question is one distinctive KB term ("consortium").
4. **Number/version guard.** A question that pins a number the matched row does not carry refuses instead of answering the sibling ("SOC 1" against a SOC 2 row, "ISO 27001", "TLS 1.3").
5. **Curated negative knowledge.** Known near-miss products the buyer might name are in the KB as explicit "not supported" rows ("Fiserv Premier" when only Fiserv DNA is vetted), so the copilot gives a definitive correct answer instead of confusing a sibling for the real thing.
6. **Twin collapse.** The same fact stored in two files (Q&A bank + capability matrix) is one result, not a false "ambiguous."
7. **Loud status labels.** Every capability answer is tagged GA / BETA / ROADMAP / NOT SUPPORTED, with a caution line for anything not generally available.
8. **Staleness flag.** A row verified more than 90 days ago is flagged "re-confirm before quoting."

## Retrieval (production hybrid)

Retrieval is where recall is won, and it is separated from the guarantee: the grounding contract (finalize) is identical no matter which retriever produced the candidates. Three retrievers share it.

**Lexical** (TF-IDF, stdlib) nails proper nouns and acronyms (Salesforce, SOC 2, Fiserv) and carries the token gate. **Dense** (`thenlper/gte-large` over a LanceDB vector store) closes the synonym and word-form gap ("operating hours" ~ "support hours"). **Hybrid** runs both pipelines through the full contract and combines their verdicts: whichever pipeline confidently answers wins, a topic-name anchor breaks a two-answer disagreement, and both refusing refuses. Union recall, and because each pipeline is tuned to zero-wrong, the union stays zero-wrong.

The embedding model was chosen by an **eval-backed bake-off** (six models, metric = max correct at `WRONG = 0`, threshold swept, same contract for all):

| model | dim | correct | synonym (of 12) | wrong |
|---|---|---|---|---|
| lexical (baseline) | n/a | 84 | 3 | 0 |
| all-MiniLM-L6-v2 | 384 | 77 | 4 | 0 |
| bge-small | 384 | 82 | 4 | 0 |
| bge-base | 768 | 85 | 5 | 0 |
| bge-large | 1024 | 86 | 7 | 0 |
| e5-large | 1024 | 84 | 5 | 0 |
| **gte-large (chosen)** | 1024 | **87** | **8** | 0 |

Two findings worth keeping. First, `all-MiniLM-L6-v2` (a common default) was the **worst**, below lexical, and at a recall-tuned threshold it answered "can your platform spot money laundering patterns?" with **check fraud** (a Beta capability) at a score higher than a correct answer elsewhere. The eval harness caught that compliance confident-wrong. Model quality is the variable, not the architecture. Second, even the best dense model alone (87) is only +3 over lexical, because dense still misses the proper nouns lexical nails. That is the case for hybrid, which lands at **89**, above either alone, still zero-wrong.

### The reranker did not earn the default

A cross-encoder rerank stage (`--rerank`, `retrieval/rerank.py`) was built and baked off the same way: union candidate generation, then a cross-encoder, then the same contract. It **underperformed** at zero-wrong: ms-marco-MiniLM 78, bge-reranker-base 81, bge-reranker-large 82, versus the ensemble's **89**. A single reranked list plus one threshold cannot match the ensemble's two independently calibrated shots, and MS-MARCO-trained rerankers are not calibrated for a small, terse fact KB (rerankers pay off on large, passage-like candidate sets). It is kept behind `--rerank` to revisit as the corpus grows; the ensemble stays the default. The eval rejected the technique, which is the point.

Still open (see ARCHITECTURE): the pgvector production store and a constrained LLM composition layer.

### Structured / deterministic layer (default; `--no-routed` to disable)

```bash
python3 -m grounded "do you support temenos t24?"   # deterministic-first, on by default
```

Some questions have exactly one correct value: whether a capability is live or roadmap, whether a certification is held, an uptime SLA, a latency number, a retention period. Those are **deterministic**, and answering them by similarity search is a needless risk. The router sends them to an **exact lookup** against structured triples and defers everything open-ended to the probabilistic retrieval path. Two triple kinds today:

- **Status**: `(entity, status, GA|Beta|Roadmap|Not-supported)`, derived from every fact's `status`. "Do you support Temenos T24?" comes back `exact (deterministic lookup)`, ROADMAP, not a confidence score.
- **Value**: a value question ("what is your uptime SLA?", "what are your operating hours?") maps by distinctive trigger tokens to the one vetted fact that holds the value.

Safety gates keep it from ever weakening the guarantee: status fires only on a uniquely-named entity (ambiguous defers), value fires only on a unique trigger match, and the number guard rides both, so "is SOC 1 certified?" cannot resolve the SOC 2 triple (it defers and refuses). Deterministic routing is **on by default** and holds zero-wrong on both bases (routed+lexical **85**, routed+hybrid **89**); on the lexical base it even recovers a synonym miss ("operating hours" resolves deterministically). The triple is just a knowledge-graph `(subject, predicate, object)`; the KB's `status` field was already one. Next: promote value triples into the KB schema itself rather than a curated declaration.

### Faithfulness verifier (`--verify`, and `verify` to calibrate)

```bash
python3 -m grounded verify              # calibrate the gate
python3 -m grounded --verify "..."      # answer with the gate on
```

The run-time twin of the eval gate: a check that an answer's claim is actually **entailed by its cited source**, run at answer time. It's built *now*, while it is a deliberate **no-op over verbatim answers** (the claim *is* the source), so it can be calibrated on known-good content and trusted before composition ever turns on. On that day the claim is a generated sentence and an unsupported one is vetoed here, before it reaches the buyer. Default is a local NLI cross-encoder (egress-safe, swappable for a MiniCheck-class faithfulness model).

Calibration (`verify`) proves the two things that make it trustworthy: over real (claim vs its own source) pairs it must not reject known-good answers, and over adversarial (claim vs an unrelated source) pairs it must reject. Current: **0 false-rejects of 85** (100% pass, so it never causes a miss) and **94% rejection of 84 mismatches** (5 generic answers weakly entail unrelated sources; tuned when generation exists).

## Use it from any agent (MCP)

Grounded is an [MCP](https://modelcontextprotocol.io) server, so any MCP client (Claude Desktop, IDEs, other agents) can call it and inherit the guarantee: one tool, `grounded_answer(question)`, returns a vetted, cited, labeled answer or an explicit refusal. It never fabricates, so an agent that calls it cannot be led into a confident wrong answer.

```bash
python -m grounded mcp        # run the server (stdio)
```

Register it in an MCP client's config (paths are for this repo; adjust to yours):

```json
{
  "mcpServers": {
    "grounded": {
      "command": "/Users/dhirajbhat/.pyenv/versions/3.11.10/bin/python",
      "args": ["-m", "grounded.mcp_server"],
      "env": { "PYTHONPATH": "/Users/dhirajbhat/Desktop/grounded" }
    }
  }
}
```

Defaults to routed + lexical (instant start, no model download, no egress). Set `GROUNDED_MCP_MODE=hybrid` in `env` for semantic retrieval.

## Live watch mode (entity-triggered)

`--watch` is the live-call form factor. It reads a transcript stream (a file, or stdin) and, for each line, fires **only when the line names a known entity** (a product, integration, acronym, or competitor the KB knows), then surfaces the grounded card for it. If nothing is vetted, it stays silent. A per-topic cooldown stops the same card firing on every mention.

```bash
python3 -m grounded --watch evals/sample_call.txt
```

On the sample call it surfaces a GA card when the prospect names "Fiserv DNA", a BATTLE CARD when they name a competitor ("SentinelIQ"), a ROADMAP card with a caution for "Temenos T24", and an honest NOT SUPPORTED for "FedRAMP". It says nothing for an unknown competitor ("FalconX") or for chit-chat.

The design is a borrowed pattern with the discipline inverted. A live copilot that fires retrieval on keywords is common; the trick here is that the trigger only *starts* the lookup, and the same cite-or-refuse engine decides whether anything is safe to show. Trigger on entities, not on question-detection (which is slow and error-prone); ground every surfaced card. The trigger is deliberately high-precision (named entities only), so a capability asked in plain words ("do you do real-time scoring") does not fire; widening the trigger vocabulary is a knob, traded against noise on a live call.

## Knowledge / ingestion layer

```bash
python3 -m grounded ingest
```

Pulls documents and transcripts from mocked enterprise sources, extracts them, and turns documents into candidate facts with provenance and a freshness class, while mining transcripts only for questions. It runs over mock fixtures (`fixtures/`); nothing is auth-wired.

- **Formats:** XLSX, PDF, DOCX are extracted for real (openpyxl / pypdf / python-docx). Cloud docs arrive as one of these through a source connector.
- **Sources:** local is real. Google Drive, SharePoint, Office 365, and the transcript/call-intel connectors (Gong, Otter, Granola, Zoom, Sybill, Wispr, Minutes) are mocked: they declare support and return fixtures, but do no auth and make no API calls. Real enterprise auth is a later step, and nothing above the connectors changes when it lands, because everything speaks `RawDoc`.
- **Provenance:** every candidate fact carries its source system, document, and exact locator (`Capabilities!row5`, `section: EU data residency`, `pages 1-1`).
- **Freshness:** each fact has a TTL by claim class (security 180d, capability 120d, pricing 90d, roadmap 60d, competitor 45d); anything past its TTL is flagged stale.
- **Source-of-truth conflict detection:** when two sources make different claims about the same topic (the Google Sheet says EU residency is Roadmap, the SharePoint doc says GA), the pipeline flags it and **holds both out of the served KB** for curation instead of silently picking one.
- **The trust boundary:** documents are vettable and can become facts. **Transcripts are untrusted** (a rep can say something wrong on a call) and never auto-promote to a fact. They are mined for the buyer questions asked, checked against the KB for **coverage and gaps**, and a human must promote anything.

### Promotion (ingestion feeds retrieval)

```bash
python3 -m grounded promote
```

Closes the loop: accepted facts (fresh, non-conflicting) are **coverage-gated** against the hand-authored KB, and only the ones the KB does not already answer are written to `kb/promoted.jsonl` and served. Duplicates are skipped; conflicts and stale facts are held. On the fixtures: 16 accepted, 15 skipped as already-covered (semantic dedup catches near-duplicates like "Encryption" vs the existing encrypted-at-rest fact), **1 net-new promoted** (`Databricks export` from the mocked Google Sheet). Before, "do you export to databricks?" refused; after, it answers GA with a citation back to `Capabilities!row9`. Both evals stay zero-wrong (lexical 84, hybrid 89).

The served KB is `kb/*.jsonl` (hand-authored) plus `kb/promoted.jsonl`, kept separate so promotion is auditable and reversible. Known limitation: semantic dedup can false-positive on sibling entities ("ServiceNow case sync" was skipped as matching the Salesforce case-sync fact); entity-aware dedup and curated negative facts are a curation-layer task.

## Layout

```
CONCEPT.md                 the pitch (thesis, market gap, defensibility)
ARCHITECTURE.md            the production design, build order, decision log
grounded/                  the package
  grounding.py             the contract: threshold, guards, labels, refusal  <- the product
  facts.py                 the Fact model + KB loader
  text.py                  tokenization + entity (strong-token) detection
  render.py                CLI + live-surface rendering, staleness
  retrieval/lexical.py     TF-IDF retriever
  retrieval/dense.py       gte-large over a vector store
  retrieval/store.py       VectorStore interface + LanceDB
  retrieval/hybrid.py      the lexical + dense ensemble (default)
  retrieval/rerank.py      experimental cross-encoder stage
  ingestion/               connectors, extract, factify, freshness, conflict, pipeline
  cli.py                   modes (one-shot, REPL, watch, eval, ingest, promote) + entry
kb/*.jsonl                 vetted facts (fictional Kestrel): qa, capabilities, competitors
kb/promoted.jsonl          facts promoted from ingestion (provenance-carrying)
fixtures/                  mock docs + transcript for ingestion
evals/eval_set.jsonl       the 118-case zero-wrong guardrail
evals/sample_call.txt      a sample transcript for --watch
```

## Not yet built (see ARCHITECTURE for the full plan)

- Cross-encoder reranker on top of hybrid retrieval.
- Knowledge/ingestion layer: provenance, freshness TTLs, source-of-truth conflict detection.
- Constrained LLM composition + claim verification (verbatim stays the default).
- Real-time transcript service; multi-tenant, audit, own SOC 2.
