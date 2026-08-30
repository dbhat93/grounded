# Grounded: Concept Pitch

**A grounded answer layer for high-trust sales. Cite the source or say "I don't know." Never confidently wrong.**

*Product name: **Grounded**. (Earlier directions considered: Vouch, Warrant, Attest, Cited, Ground Truth, Vetted.)*

*This is a clean-room concept document. It contains a thesis, a market read, and an architecture principle. It contains no proprietary data, no company knowledge base, no third-party code, and names no employer. Everything here is generalizable know-how offered by the originator to a founder who could build it.*

---

## The one line

Every AI sales tool on the market optimizes for volume: more dials, more demos, more pipeline. In regulated and high-trust selling, the expensive failure is not too few conversations. It is one confidently wrong answer in front of a buyer who cannot tolerate it. Grounded is the first sales-AI layer built trust-first. It answers only from vetted, cited knowledge, labels what is live versus what is roadmap, and refuses rather than guesses. It is designed so it cannot present an unverified claim as fact.

## The 90-second version (say it out loud)

*Roughly 230 words. This is the spoken pitch when someone asks "what's the idea."*

Every AI sales tool on the market is built to do more. More calls, more demos, more pipeline. And for most software that is fine.

But the interesting rooms are the regulated ones. Banks, credit unions, the kind of buyer where one wrong answer ends the deal. In that room, volume was never the problem. The problem is a rep who confidently says "yes, we do that" about something we do not do. That loses the deal, and sometimes it is a compliance event.

Nobody is building for that. So here is the idea.

A sales copilot where being correct is the product. It answers only from vetted, cited knowledge. It labels what is live versus what is roadmap. And when it does not know, it says so, instead of making something up. You can put a brand-new rep in a hard room and they will be as accurate as your best veteran, because the system behind them will never let them guess.

Here is the part that makes it a company. The market has split in two. One camp does AI roleplay and coaching but never checks whether the answer is true. The other does grounded, cited answers but coaches no one. Nobody is in the middle. That middle, coaching plus answers you can trust, is the whole thing, and it is empty.

I am not the person to run it day to day. But I know exactly how it is built, and I know the vertical. I am looking for the person who can.

## The insight (the wedge)

Large language models made one thing cheap and universal: fluent, plausible, and often wrong answers. For most software that is a tolerable trade. For a rep sitting across from a bank, a hospital system, an insurer, or a government buyer, it is a deal-killer and sometimes a compliance event. A single "yes, we do that" about a feature that is not shipped, or a misstated security answer, can lose the deal and damage the vendor's credibility for years.

The whole AI-sales category has looked away from this. The tools are racing to generate more: more outreach, more meetings, more auto-run demos. None of them is built so that being *correct* is the product. That is the gap.

The reframe: in high-trust verticals, the constraint was never conversation volume. It is answer quality under scrutiny. Solve that, and you can put a junior rep in a high-stakes room and have them be as grounded and credible as a twenty-year veteran, because the system behind them will only ever surface a vetted, cited, correctly-labeled answer, or nothing.

## Why now

- LLMs put "helpful but plausibly wrong" into every sales workflow overnight. The pain is fresh and growing.
- Regulated buyers are exactly the segment that cannot absorb that error, and they are exactly the segment every enterprise software vendor is trying to sell into.
- The current market answer to hallucination is a disclaimer and a shrug. There is room for a product whose entire promise is the opposite.

## The market gap, in evidence

A scan of what a high-trust sales team can actually buy today:

- **Volume dialers and floors** (for example Nooks): built for teams making hundreds of calls a day. Coaching is a companion feature on a firehose.
- **Conversation intelligence** (for example Gong, Clari Copilot): strong post-call analytics; live coaching is thin or enterprise-gated, and none is grounded against a vetted, cite-or-refuse knowledge base.
- **Autonomous demo agents** (for example Supersonik): an AI that runs the demo itself. Novel, but improvising an unscripted pitch in front of a regulated buyer is the opposite of what a trust-first buyer wants.
- **Revenue-platform replacements** (for example Monaco): rip-and-replace the CRM and the whole stack. Aimed at founders with no sales motion, not teams that need answer quality.
- **Async demo automation** (for example Consensus): scales top-of-funnel demo requests. A volume solution.
- **Real-time meeting copilots** (for example Winn.ai, and now Zoom's own ZoomMate): join the live call, guide the rep through a playbook, flag objections in the moment, and auto-update the CRM afterward. This is the closest thing on the market to the form factor here, and it is the most instructive. The live experience is right. Winn even pulls live answers from the customer's own knowledge base, so it is partially grounded. But it still has no answer-level citation, no live-versus-roadmap labeling, and no refuse-when-unsure, so it will state a wrong or stale fact in front of the buyer as confidently as a right one. Right interface, half the discipline.

Every one of them is a volume or generic-assist tool. Not one is built so that provable correctness is the core value. That absence is the company.

*Market scan refresh (Aug 2026):* the live-copilot category is filling in fast. Zoom shipped its own in-meeting assistant, ZoomMate (the rebrand of AI Companion, around $20 per user), and Winn added knowledge-base-grounded live answers. The form factor is commoditizing. What none of them added is the discipline: cite the exact source, label live versus roadmap, refuse when unsure. Watch the name collisions too: Hyperbound (sales roleplay, and explicit that it does not train on your data) sits in the coaching camp, and HyperVerge is an unrelated identity-verification/KYC vendor, not a sales tool at all.

## The product

### Wedge: the grounded demo and call copilot

A rep is in a live demo or discovery call. A hard question comes: a specific integration, a security posture, an ROI number, a "can it do X." The copilot, running on a screen the prospect cannot see or inside the team's chat, returns the vetted answer with its source cited and a clear label for whether the capability is live or on the roadmap, or it says plainly "not in our knowledge base, follow up in writing." It never fabricates to fill the silence.

Two surfaces from day one:
- **Live**, during the call, glance-able, no typing required (a rep reflecting the question back can be the trigger, or a bot that joins the meeting and follows along).
- **Async**, in the team's chat tool, on demand and optionally proactive, so knowledge and prep are one message away and a new hire is productive on day one.

One hard adoption lesson: the live surface has to work for a non-technical rep out of the box. If standing it up takes engineering or a developer's toolchain, only the builders use it and it never reaches the floor. Productizing the form factor for a salesperson is its own work item, separate from making the brain correct.

### Platform: one grounded engine, a suite of surfaces

The same verifiable knowledge core extends into the rest of the high-trust go-to-market workflow. This is the full scope of the originator's work, generalized:

1. **Grounded live and async copilot** (the wedge above).
2. **Automated pre-engagement research and prep briefs.** Pull structured intelligence about a target account from multiple sources into a single briefing, so a rep walks in with context instead of conjecture, and a junior rep walks in with the same context a veteran would assemble by hand.
3. **Exec and revenue-review synthesis.** Turn CRM records and call intelligence into a leadership-ready review: deal health, risks, stalls, and recommended actions, generated rather than hand-built for every pipeline meeting.
4. **Post-call performance scoring and coaching.** Score a call against a rubric, extract what worked, and feed it back so reps improve. The training loop that makes ramp fast.

The connective tissue under all four is the part that is hard to copy: a single vetted knowledge layer plus an evaluation harness that continuously proves the system does not present unverified claims as fact. The harness is fed by a golden question set mined from the team's own historical sales calls (via a conversation-intelligence tool), with every question checked to have a backing source in the knowledge layer. That turns the archive of past deals into the eval backbone, and it is a repeatable pipeline rather than a one-time content push. The Feature Value Map (what is live versus roadmap, per capability) is one of the most load-bearing sources feeding it.

The same loop should run live, not just off the archive. A rep's thumbs-up or thumbs-down on an answer during the call is signal, and it should do real work: an up-vote promotes that answer into the golden set as a regression test, a down-vote routes its source to a fix queue for curation, and repeated down-votes on the same cue flag the content as wrong, stale, or mis-retrieved. Human-gated, never auto-learned, and never allowed to override the cite-or-refuse floor (popularity must not surface a wrong answer). The lesson learned the hard way: a feedback control that only hides a cue or resets a counter wastes the signal. The point of the click is to make the next answer better, so every up-vote and down-vote has to feed the same knowledge-and-eval flywheel.

## The architecture, at a high level

Five layers, kept deliberately separable so the discipline never depends on any one model or vendor:

1. **Capture and interface.** Something follows the live conversation and turns it into detected questions and moments: a participant that joins the meeting, a local listener on the transcript, or a simple reflection trigger where the rep repeats the question back. Output lands on a glance-able surface during the call and in a chat surface for async. Knowing who asked what (speaker attribution) matters.

2. **Question routing, then retrieval and answer.** First, classify the question. Some questions have exactly one correct value: a routing number, a specific rate, whether a capability is live or roadmap. These are deterministic, and the right behavior is an exact lookup against a structured fact, with nothing generated. The rest are open-ended and go to retrieval over prose, on a spectrum of two modes chosen per deployment:
   - *Extractive:* plain lexical retrieval that returns a pre-vetted, stored answer as written. Nothing is generated at answer time, so it can run fully local with nothing leaving the environment. Lowest fabrication risk; the trade-off is weaker recall on loosely-worded questions.
   - *Retrieval-augmented:* semantic (embedding) retrieval, optionally with a model composing or verifying over the retrieved passages. Stronger recall on paraphrase, but it invokes a model, and unless that model is self-hosted, data leaves the environment.
   The retrieval choice is a trust-versus-recall-versus-egress lever, not a religion. A regulated, no-egress deployment leans extractive or a local embedding model; a higher-recall deployment can use hosted retrieval-augmentation, but only behind the guardrails below. Either way the system renders vetted content rather than inventing it, and a deterministic question never takes the probabilistic path.

3. **The discipline layer (independent of the retrieval mode).** Cite the source or refuse. Label what is live versus roadmap. Route gated topics (price, legal, security specifics) to a human. Verify that every concrete claim traces back to a source, and abstain when it does not. This layer is what makes the thing safe, and it is identical whether retrieval is extractive or augmented.

4. **The knowledge layer.** Curated, vetted sources with provenance and freshness gates: a capability map of what is live versus roadmap, an integration matrix, product fact sheets, a question-and-answer and objection corpus, and competitive cards. The answer is only ever as good as this layer, so curation is a first-class, ongoing job. Where facts are structured (a routing number, a rate, a live-versus-roadmap flag), model them as typed entities and their properties, not just as prose. That structure is what lets the deterministic path look a value up exactly, and it is what makes conflict detection precise: when two sources assert a different value for the same property of the same entity, that is a catchable conflict, surfaced for a human to resolve into the one canonical source of truth rather than silently picked. Free-text facts still live as cited passages; the structured layer sits on top for the questions that have a single right answer.

5. **Eval and the feedback flywheel.** A golden question set (mined from historical calls and grown by promoting up-voted live answers), an adversarial eval gate that must show zero confidently-wrong answers before anything ships, and the live feedback loop described above.

The property that matters is separability: the guardrails, the knowledge, and the eval are independent of the retrieval mechanism and the model behind it. That is what lets the same product run as a fully local, no-egress deployment for the most sensitive buyer and as a higher-recall hosted deployment elsewhere, without ever changing the promise that it will not present an unverified claim as fact.

## Why it is defensible

The moat is not the model. Anyone can call an LLM. The defensibility is three things that compound:

1. **Trust as an engineered property, not a marketing claim.** The grounding discipline (answer only from cited sources, verify every concrete claim traces back to its source, refuse when it does not) plus an adversarial eval harness that drives confidently-wrong answers toward zero. "Never wrong out loud" with a test suite standing behind it. A competitor bolting a "grounded mode" onto a volume tool is retrofitting the hardest property last. The same discipline is the launch gate: the bar to go live is passing the eval, not nailing the demo. A team would rather tell a buyer "I will follow up in writing" than surface a wrong answer, so shipping is gated on the eval set, not on a good rehearsal, and hardening a demo into something an examiner-facing rep can trust is deliberately treated as non-trivial, multi-week work rather than a weekend polish.
2. **Vertical knowledge depth.** The value is only as good as the curated, current knowledge behind it. Depth in a specific regulated vertical is a real barrier and a real switching cost.
3. **Workflow lock-in across surfaces.** Once the copilot, the prep, the exec review, and the coaching all run on one grounded core, the team's daily motion lives inside it.

## Why the intersection is empty

This is the strongest defensibility argument, because it is observable in the market right now, not a claim about the future.

Two layers make the product work: a **grounded knowledge layer** (answers only from vetted sources, cited, labeled live-vs-roadmap, refuses when it does not know) and a **coaching and enablement layer** (roleplay, scoring, ramp, live guidance). Scan the market and every serious player sits firmly in one circle or the other. Nobody sits in the overlap.

**The coaching and roleplay camp** (Hyperbound, GuruNow, Solidroad, Amotions, Nooks, Second Nature) simulates a buyer, scores the rep, and coaches the gap. None of them guarantees the factual correctness of the answers a rep actually gives. Hyperbound states outright that it does not train on your data and runs on its own pre-trained models, with no citations and no factual verification. Amotions comes closest to the middle with live mid-call guidance, but its prompts are drawn from captured playbooks and a behavioral-science model, not a cite-or-refuse verified knowledge base, so there is no accuracy guarantee and no "I do not know."

**The grounded knowledge camp** (Guru's Verified RAG, Glean, Tribble) delivers cited, permission-aware, freshness-gated answers. But these are knowledge bases and answer engines. None of them roleplays, scores a rep, or runs a ramp program.

The overlap of those two circles is where this product lives, and today it is unoccupied. The specific capability at the center, a roleplay that grades a rep on whether they stayed factually grounded under pressure, exists in no product on either side.

**A third reference point, the live-answer copilots** (Parakeet, Cluely, Final Round, Zoom's own ZoomMate, and the sales-native Winn.ai). These have the form factor this product wants: a live overlay, or in Winn's and ZoomMate's case a meeting participant, that follows the conversation and surfaces guidance in seconds. Winn goes further than the generic ones, tracking a sales playbook live, syncing the CRM, and pulling live answers from the customer's own knowledge base, so it is partially grounded. But none of them cite at the answer level, label live versus roadmap, or refuse when unsure. They will surface an answer whether or not it is current or true. That is the exact failure this product exists to prevent, so they are not a competitor, they are the cautionary example: the right interface wrapped around a weaker discipline. The move is to borrow the interface, and Winn's playbook-coverage idea, and invert the discipline, a live whisper and a live playbook on top of a cite-or-refuse brain rather than a free-generating or lightly-grounded one.

**Why the gap persists** (and why it is a moat, not just a window):
- The grounded half is the hard, unglamorous one. Curation, verification, freshness gates, and refusal discipline are real engineering and real operational work. The roleplay camp's entire DNA is simulation, so bolting grounding on means reversing the hardest part last.
- The fused product's value is highest in regulated and high-trust verticals, where a wrong fact is existential. That is a narrower wedge than the horizontal roleplay market the coaching camp is chasing, so those players have no reason to build toward the middle. This company would start where they will not.

**The honest version of the threat:** the two halves both exist, just apart. A funded player could fuse them. Amotions is one grounding layer away; Guru is one coaching layer away. So the defense is not "nobody thought of it." It is depth in one regulated vertical, fast enough that being the trusted, correct system of record in that vertical is the barrier, before a horizontal player decides the hard middle is worth it.

## Who buys it

Vendors and teams that sell into regulated or high-trust buyers, where a wrong answer is expensive: financial services, healthcare and health tech, insurance, government, legal and compliance software. Land in one vertical where the founding team has genuine depth, win on being unmistakably *theirs and correct*, then widen.

Enter with the copilot wedge because the pain is sharp and the demo is obvious ("watch it refuse to guess"). Expand into the prep, review, and coaching suite once the grounded core is trusted.

## Business model

Per-seat for the reps who use the copilot and the suite, plus a platform fee for the grounded knowledge core and its maintenance. Be honest that early on this is knowledge-curation-heavy and may carry services to stand up a vertical's knowledge base. That services drag is also a moat: it is the depth competitors will not want to do.

## The honest risks

An operator will ask these, so here they are first:

- **Feature, not company?** A big incumbent could add a "grounded answers" mode. Counter: trust-first is an architecture, not a toggle, and the vertical depth plus the multi-surface suite is more than a feature. Still the central risk to disprove early.
- **Incumbents move.** Gong or Clari could aim at this. Counter: they are optimized for volume and analytics; reversing to correctness-first cuts against their DNA and their existing customers' expectations.
- **Knowledge curation cost.** The system is only as trustworthy as the knowledge behind it. Counter: build the ingestion, the freshness gates, and the "this is stale, refresh it" discipline into the product so curation is cheap and safe, not manual and risky. A practical accelerant: seed both the knowledge and the golden eval set from the team's existing call archive and prior answers, so curation starts from what has already been said in real deals rather than a blank page.
- **Trust is hard to sell.** "We are correct" is a quieter pitch than "3x your pipeline." Counter: the demo does the selling. Watching an AI refuse to fabricate in front of a regulated buyer is a visceral, memorable moment.
- **"Why not just buy a real-time copilot like Winn.ai?"** The obvious operator objection, since a live playbook copilot can be bought off the shelf today, and Winn even grounds its live answers in the customer's knowledge base. Counter: buy Winn for a generic sales team where a confident wrong answer is a bad look. In a regulated FI, that same wrong answer on a live member or buyer call is a compliance and reputational event. Pulling from a knowledge base is not the same guarantee as citing the exact source, labeling live versus roadmap, and refusing when unsure. The differentiator is not the live overlay, which is now commodity, it is the cite-or-refuse, GA-vs-roadmap-labeled brain underneath it, which the volume and generic-assist players are structurally not built to add. Match their live experience, add the one guarantee they cannot.

## What exists today

Nothing that ships with this. On purpose.

The conviction and the blueprint come from the originator having built and validated every one of these patterns firsthand in a live, regulated enterprise sales setting: the grounded cite-or-refuse copilot, the eval harness that proves it does not lie, the multi-source prep automation, and the exec-review synthesis. That is where the certainty that this works comes from.

This document, and anything the originator contributes, is deliberately clean-room: the concept, the market read, and the architecture principle only. No prior employer's data, knowledge base, code, or confidential material is included or would be used. A build starts from a blank repository and the blueprint, nothing else.

## The ask and the structure

Seeking a founder-operator, able to incorporate and run the company (the originator is not seeking to operate it day to day).

The originator contributes, as a passive founder or advisor with equity rather than an operating role:
- the thesis and the conviction that the gap is real,
- the architecture blueprint for the grounded core, the eval discipline, and the suite,
- vertical go-to-market insight into how high-trust buyers actually evaluate and buy.

Structure to get right up front: the originator's stake papered before any code is written (advisor or founder equity with vesting, in writing), and everything kept clean-room so provenance is never in question.

---

*Originated by Dhiraj Bhat. Contact: [add].*
*Status: concept. Next step: pressure-test the "feature vs company" question with two or three operators who sell into a regulated vertical, and a build-vs-partner read on the knowledge-curation engine.*
