// Adversarial gate for the in-browser demo engine (demo/index.html), mirroring
// the Python eval: the same grounding contract must never be confidently wrong.
// It extracts the real answer() engine straight out of the published HTML (no
// copy to drift) and runs a broad case table through it. WRONG must be 0.
//
//   node tests/test_demo_engine.mjs
//
// Classification per case (expect = a fact id, "REFUSE", or {oneof:[...]}):
//   CORRECT     answered with the expected id
//   REFUSED_OK  expected REFUSE and it refused
//   MISS        expected an answer but it refused (safe, not harmful)
//   WRONG       answered the wrong fact, or answered when it should refuse  <- gate
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "..", "demo", "index.html"), "utf8");

// Slice out the DOM-free engine: from the FACTS table down to the first line
// that touches the document. eval it in an isolated scope and hand back answer().
const start = html.indexOf("const FACTS = [");
const end = html.indexOf("const elResult");
if (start < 0 || end < 0 || end < start) {
  console.error("FAIL: could not locate the engine in demo/index.html");
  process.exit(2);
}
const engineSrc = html.slice(start, end);
const answer = new Function(engineSrc + "\nreturn answer;")();

const CASES = [
  // --- GA answerables -----------------------------------------------------
  { q: "Do you integrate with Fiserv DNA?", expect: "INT-01" },
  { q: "Do you support Jack Henry Symitar for credit unions?", expect: "INT-02" },
  { q: "Do you work with credit unions?", expect: { oneof: ["INT-02"] } },
  { q: "Do you have a Salesforce integration for case sync?", expect: "INT-05" },
  { q: "Do you support real-time webhooks for fraud alerts?", expect: "INT-06" },
  { q: "Do you integrate with Plaid for identity verification?", expect: "INT-07" },
  { q: "Can you export data to Snowflake?", expect: "INT-09" },
  { q: "Are you SOC 2 Type II certified?", expect: "SEC-01" },
  { q: "Are you PCI DSS compliant?", expect: "SEC-02" },
  { q: "Where is customer data hosted?", expect: "SEC-03" },
  { q: "How is data encrypted at rest and in transit?", expect: "SEC-06" },
  { q: "Do you support SSO and SAML?", expect: "SEC-07" },
  { q: "What is your default data retention policy for PII?", expect: "SEC-08" },
  { q: "Do you do real-time transaction fraud scoring, and how fast?", expect: "CAP-01" },
  { q: "Do you support device fingerprinting?", expect: "CAP-02" },
  { q: "Do you do AML transaction monitoring?", expect: "CAP-05" },
  { q: "Do you have case management and investigation workflow?", expect: "CAP-07" },
  { q: "Can analysts author their own custom rules without engineering?", expect: "CAP-08" },
  { q: "What is your uptime SLA?", expect: "COM-01" },
  { q: "What are your support hours?", expect: "COM-02" },
  { q: "How long does implementation take?", expect: "COM-03" },
  { q: "What is your pricing model?", expect: "COM-04" },

  // --- Beta (must be labelled Beta, i.e. its own row, not a GA sibling) ----
  { q: "Do you integrate with the FIS Horizon core?", expect: "INT-03" },
  { q: "Do you detect check fraud?", expect: "CAP-03" },

  // --- Roadmap (phrased as if it might be live) ----------------------------
  { q: "Do you support Temenos T24?", expect: "INT-04" },
  { q: "Do you support EU data residency or hosting outside the US?", expect: "SEC-04" },
  { q: "Do you offer consortium or shared cross-institution fraud signals?", expect: "CAP-04" },

  // --- Honest negatives (curated 'no' rows) -------------------------------
  { q: "Are you FedRAMP authorized?", expect: "SEC-05" },
  { q: "Do you automatically file SARs with FinCEN?", expect: "CAP-06" },
  { q: "Do you integrate with Fiserv Premier?", expect: "NEG-01" },
  { q: "Do you integrate with Fiserv Signature?", expect: "NEG-02" },
  { q: "Do you integrate with Jack Henry SilverLake?", expect: "NEG-03" },
  { q: "Do you support Temenos Infinity?", expect: "NEG-04" },
  { q: "Do you integrate with Corelation Keystone?", expect: "NEG-05" },

  // --- Battle cards -------------------------------------------------------
  { q: "How do you compare to SentinelIQ?", expect: "COMP-01" },
  { q: "What about FraudFort?", expect: "COMP-02" },

  // --- Near-miss entity traps (the confident-wrong class) -----------------
  // Misheard core, but names a distinct entity: must NOT return the Symitar GA.
  { q: "and what about correlation keystone, that's our credit union core?", expect: "NEG-05" },
  { q: "we're a credit union on Keystone, do you plug into it?", expect: { oneof: ["NEG-05"] } },

  // --- Number / version traps (must refuse, never resolve a sibling) ------
  { q: "Are you SOC 3 certified?", expect: "REFUSE" },
  { q: "Are you SOC 1 certified?", expect: "REFUSE" },
  { q: "Are you ISO 27001 certified?", expect: "REFUSE" },
  { q: "Do you support TLS 1.3?", expect: "REFUSE" },
  { q: "Are you PCI DSS Level 2 certified?", expect: "REFUSE" },

  // --- Off-domain / unknown / leading absolute-claim traps ----------------
  { q: "Do you integrate with SAP ERP?", expect: "REFUSE" },
  { q: "Do you support SAP Ariba?", expect: "REFUSE" },
  { q: "Do you integrate with Backbase?", expect: "REFUSE" },
  { q: "Can you guarantee 100% fraud detection?", expect: "REFUSE" },
  { q: "Can you guarantee we pass our next regulatory audit?", expect: "REFUSE" },
  { q: "What is your parental leave policy?", expect: "REFUSE" },
  { q: "What's the weather in Chicago today?", expect: "REFUSE" },
  { q: "How do you compare to FalconX?", expect: "REFUSE" },

  // --- Paraphrase recall (MISS is safe; WRONG is not) ---------------------
  { q: "What are your operating hours?", expect: { oneof: ["COM-02"] } },
  { q: "How quickly do you score a transaction?", expect: { oneof: ["CAP-01"] } },
];

let correct = 0, refusedOk = 0, miss = 0, wrong = 0;
const wrongRows = [], missRows = [];

for (const c of CASES) {
  const r = answer(c.q);
  const got = r.kind === "answer" ? r.fact.id : null;
  if (c.expect === "REFUSE") {
    if (r.kind === "refuse") refusedOk++;
    else { wrong++; wrongRows.push([c.q, "REFUSE", got]); }
    continue;
  }
  const accept = typeof c.expect === "object" ? c.expect.oneof : [c.expect];
  if (r.kind === "refuse") { miss++; missRows.push([c.q, accept.join("/")]); }
  else if (accept.includes(got)) correct++;
  else { wrong++; wrongRows.push([c.q, accept.join("/"), got]); }
}

console.log("Demo-engine eval over %d cases  [demo/index.html answer()]", CASES.length);
console.log("  CORRECT     %d  (right answer, right row)", correct);
console.log("  REFUSED_OK  %d  (correctly said 'not in the KB')", refusedOk);
console.log("  MISS        %d  (refused when it could have answered; safe)", miss);
console.log("  WRONG       %d  (confident-wrong or answered-when-should-refuse; MUST be 0)", wrong);
if (missRows.length) {
  console.log("\n  Misses (safe, refused instead of answering):");
  for (const [q, exp] of missRows) console.log("    - %o  (could have been %s)", q, exp);
}
if (wrongRows.length) {
  console.log("\n  Confident-wrong cases:");
  for (const [q, exp, got] of wrongRows) console.log("    - %o  expected=%s  got=%s", q, exp, got);
}
console.log("\n  Result: %s", wrong === 0 ? "PASS (zero wrong)" : "FAIL (see above)");
process.exit(wrong === 0 ? 0 : 1);
