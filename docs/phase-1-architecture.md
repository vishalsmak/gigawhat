# GigaWhat Phase 1: architecture proposal

| | |
|---|---|
| Status | Agreed 14 October 2026, with the defaults in section 10 for Q1 to Q11. Phases 2a (model providers) and 2b (layer split) are built; see section 9. |
| Answers | `docs/project-brief.md`, section 10 ("Your first deliverable") |
| Baseline | Commit `950cfac`, plus the uncommitted `GIGAWHAT_RERANKER` setting |
| Labels | **A** assumption, **D** decision already made by the owner, **P** proposal, **Q** open question (section 10) |

GigaWhat already exists and works. This proposal restructures it into the layers the brief asks for and closes the gaps between what it does and what the brief requires. It is not a rewrite: anything that already meets the brief stays, and every move is checked against the existing tests and evaluation.

## 1. Problem statement and assumptions

### Problem

Staff at a regulated gas and electricity utility need to find the approved procedure for a job, understand the evidence behind it and justify their next step, quickly and without the assistant taking the decision from them. The risk is asymmetric: a slow answer costs minutes, while a wrong, stale or unauthorised one can hurt someone or breach a permit-to-work system. The assistant therefore has to be a governed decision-support system: it retrieves only what the user may see, answers only from current approved sources, shows its evidence, says when it doesn't know, and hands safety-critical, contradictory or ambiguous cases to a human.

### Starting point (confirmed)

| Area | What exists | Evidence |
|---|---|---|
| Workflow | 14-step LangGraph graph: emergency screen, input guardrail, risk tier (rules plus a model, stricter wins), hybrid retrieval, an evidence agent over operational records, cited answers, a verbatim lane for safety-critical questions released by an Authorised Person, and an audit step | `src/gigawhat/assistant/graph.py` |
| Retrieval | Vector and full-text search merged by reciprocal rank fusion, reranked, cut at relevance 0.2; row-level security by business unit; drafts hidden unless allowed | `retrieval/search.py`, migration `0004` |
| Document control | A register decides each version's status (approved, superseded, withdrawn, draft), owner, review date and scope | `data/corpus/register.yaml` |
| Verification | Every quote is checked against its source; claims whose quotes don't match are dropped; a conflict needs two distinct documents | `assistant/answer.py` |
| Oversight | Approvals table, append-only audit of every question, a pause switch | `assistant/oversight.py`, `service.py` |
| Evaluation | 60 golden and 25 red-team cases, five hard release gates; the offline profile passed all five on 10 October 2026 | `evals/`, `docs/governance/evaluation-report.md` |
| Tests | 343 passing; ruff and mypy strict clean | `tests/` |

### Gaps against the brief

| Brief | Gap |
|---|---|
| §4D step 9, §5 scenario 3 | No **clarification** outcome. The golden set has no ambiguous-question cases. |
| §3, §4D | Escalation exists only for safety-critical questions (to an Authorised Person). Ambiguous, contradictory and out-of-scope questions abstain or are refused, but are **not routed to a named human or process**. |
| §4E, §4F | Conflicts are found only by the model and then checked in code. **Nothing declares** which documents conflict or which wins, so a missed conflict is silent. |
| §3, §4C | Access control is **per business unit**, not per document. |
| §4E | Answers have claims, steps and conflicts, but not the brief's six parts (answer, evidence, sources, next steps, limitations, escalation). |
| §4F | Validation is mixed into answer generation rather than a **separate layer** with named checks and outcomes. |
| §4H | No structured logging, metrics or **cost tracking**; the audit table is the only operational record. |
| §5 | Evaluation is end-to-end only. There is **no retrieval-level** measure (recall of the right section). |
| §6 | Models are chosen by a two-value profile, not a **per-role provider abstraction**. The first cloud run failed on a provider limit no check anticipated (Groq free plan: 11,791 tokens requested against 8,000 a minute). |
| §7 | Modules are grouped by history (`assistant/` holds orchestration, generation, policy and validation), not by the brief's layers. |

### Assumptions

| ID | Assumption |
|---|---|
| A1 | The fictional GigaWhat Energy corpus and records stand in for a real document management system and asset systems, and stay labelled as fictional (brief §9 rule 9). |
| A2 | UK context: HSE guidance, the Electricity at Work Regulations, gas safety regulations, UK GDPR. |
| A3 | Users are the six existing personas. A pilot means at most 50 users, a few at once, and up to about 5,000 document versions. |
| A4 | English text documents (Markdown and PDF). Drawings and schematics are out of scope. |
| A5 | No connection to plant, OT, SCADA, work-management or permit systems. Records are read-only copies. |
| A6 | No identity provider is available yet. Choosing a persona in the demo is a labelled stand-in behind an interface. |
| A7 | Users are online. Offline field use waits until a pilot workflow needs it. |
| A8 | Model spend during development is zero (decision D2). |
| A9 | Hosting is undecided and must be cheap. One small server is acceptable for the demo and pilot. |
| A10 | The register is the source of truth for status. **Which document wins in a conflict is not defined** and must come from the document owners (Q1). The assistant must not invent a hierarchy. |
| A11 | Targets: emergency card under 1 second; median answer under 10 seconds on a cloud model. |
| A12 | Real personal data is not intended but can be typed in, so masking stays mandatory. |

### Decisions already made by the owner

| ID | Decision | Date |
|---|---|---|
| D1 | Keep NeMo Guardrails, DeepEval and the offline (Ollama) profile. Langfuse, Anthropic and the production Terraform are removed. | 12 Oct |
| D2 | Zero model spend for now. The development chat model is the **Gemini free tier**, once its current limits are confirmed. Embeddings stay on OpenAI (about a cent for the corpus). Reranking is local. | 14 Oct |
| D3 | Hosting comes after the system runs end to end on the cloud profile. AWS is no longer assumed; the AWS Terraform, deploy scripts and old explainer page were deleted. | 14 Oct |
| D4 | Fast role on `gemini-3.1-flash-lite`, answer role on `gemini-3.5-flash-lite`: free-tier quotas are per model, so each role gets its own 500 requests a day (measured limits: 15 a minute, 500 a day; the full Flash models allow only 20 a day). Groq stays selectable per role. | 14 Oct |
| D5 | LangSmith traces everything on the cloud profile; the demo account is in the US region, which is acceptable for fictional data. On the cloud profile each evaluation run is a LangSmith experiment. | 14 Oct |

## 2. Proposed architecture

### Principles (P)

1. **Deterministic control around probabilistic parts.** Rules, permissions, status filters and validators decide what happens. Models classify, rewrite, select records and draft text inside those limits.
2. **One database.** PostgreSQL with pgvector holds content, vectors, full-text indexes, access policies, records, approvals, audit and workflow checkpoints. That makes one thing to secure and back up, and access is enforced below the application.
3. **Access is enforced before the model sees anything.** Row-level security filters every query by the user's principal. The model is never asked to respect permissions.
4. **Every model sits behind a role.** The fast checks, the answer writer, embeddings and the reranker are configured separately, so a provider can be swapped (D2) without touching the workflow.
5. **Validate before display.** A response that fails a critical check is withheld or escalated, never shown with a warning.
6. **Measure at three levels**: retrieval, generation and end-to-end, with hard gates for failures that must never happen.

### Component diagram

```
 Staff (browser)
      |
      v
+------------------------------------------------------------------------------+
| INTERFACE        Chat UI (Chainlit, demo)        HTTP API (FastAPI)          |
+------------------------------------------------------------------------------+
      | question + principal
      v
+------------------------+    +------------------------------------------------+
| IDENTITY & ACCESS      |    | POLICY  (deterministic, versioned config)      |
| principal: roles,      |    | emergency rules, risk tiers, scope,            |
| units, documents,      |    | escalation routes, prohibited directives       |
| Authorised Person      |    +------------------------------------------------+
+------------------------+                       |
      |                                          |
      v                                          v
+------------------------------------------------------------------------------+
| ORCHESTRATION   LangGraph state machine, checkpointed in Postgres            |
|  screen -> check input -> classify -> retrieve -> assess evidence ->         |
|  generate -> validate -> answer | clarify | abstain | escalate | release     |
+------------------------------------------------------------------------------+
     |              |               |                |                 |
     v              v               v                v                 v
+----------+  +-----------+  +-------------+  +-------------+  +---------------+
| RETRIEVAL|  | RECORDS   |  | GENERATION  |  | VALIDATION  |  | OVERSIGHT &   |
| hybrid,  |  | read-only |  | typed       |  | named       |  | AUDIT         |
| RLS,     |  | tools     |  | drafts,     |  | checks with |  | approvals,    |
| rerank,  |  |           |  | verbatim    |  | outcomes    |  | append-only   |
| assess   |  |           |  | lane        |  |             |  | events        |
+----------+  +-----------+  +-------------+  +-------------+  +---------------+

 Retrieval, policy and generation call MODEL PROVIDERS by role:
   fast (tier, input check, rewrite) | answer | embeddings | reranker

+------------------------------------------------------------------------------+
| POSTGRESQL + PGVECTOR   documents, versions, chunks (vector + full text),    |
| access policies (RLS), records, approvals, audit, workflow checkpoints       |
+------------------------------------------------------------------------------+
      ^
      | activate and retire versions
+------------------------------------------------------------------------------+
| INGESTION (batch)  source adapter -> parse -> validate metadata -> dedupe -> |
| chunk -> embed -> index -> activate; a run report and audit for each run     |
+------------------------------------------------------------------------------+

 Alongside: EVALUATION HARNESS (datasets -> runs -> reports and gates)
            OBSERVABILITY (structured logs, metrics, LangSmith traces on cloud)
```

### What changes from today (P)

| Component | Today | Proposed | Why |
|---|---|---|---|
| Interface | Chainlit calls the assistant in process. The API has `/health` and `/api/audit`. | The API owns question, approval and audit endpoints. Chainlit uses the same service interface. | §4G, §7: replaceable UI, testable API |
| Identity | Persona picker and cookie. RLS by business unit. | A `Principal` from an `IdentityProvider` (demo stand-in now, OIDC later). Document-level access entries alongside units. | §3, §4C |
| Policy | Tier rules in YAML plus a classifier. NeMo input rail. Escalation only to an Authorised Person. | One policy module: emergency rules, tiers, scope, **escalation routes** (who, for what, how), prohibited directives. Versioned like prompts. | §3, §7: explicit, testable rules |
| Retrieval | Returns passages and a "sufficient" flag. | Returns an **evidence assessment**: relevance, coverage, authority (current, overdue, recently revised), declared conflicts, and a sufficiency verdict with reasons. | §4C: report weakness, don't force a result |
| Orchestration | 14 nodes. No clarify or general escalate. | Adds `assess_evidence`, `clarify`, `escalate` and a separate `validate` step. | §4D steps 5, 6, 8, 9 |
| Generation | Claims, steps, conflicts, gaps. | The brief's six-part answer. The verbatim lane stays. | §4E |
| Validation | Quote checks inside `answer.py`. | A separate layer of named validators, each with an outcome: pass, repair, withhold or escalate. | §4F |
| Audit and observability | Audit events per question. Optional traces. | Audit events per workflow transition and validation outcome. Structured JSON logs with redaction. Metrics for latency, tokens and cost per provider. | §4H |
| Providers | `cloud` or `offline` profile with fixed models. | A model registry per role, with a capability and limit check at start-up. Gemini added for development (D2). | §6, and the Groq failure |
| Ingestion | Register-driven, skips unchanged versions by content hash. | A source-adapter interface, a metadata validation report, explicit activation and retirement of versions, and an audit record for each run. | §4B |
| Evaluation | End-to-end cases and five gates. | Adds retrieval-level and validation-level suites, clarification cases and three new gates. | §5 |

## 3. Request and response flow

Diagram: `docs/diagrams/request-flow.mmd` (Mermaid source) and `docs/diagrams/request-flow.png`.

1. **Receive.** The API authenticates the caller and builds a `Principal`. Personal data in the question is masked (Presidio) before anything is stored or sent to a model.
2. **Screen.** Deterministic emergency rules run first. A match returns the emergency card at once, with no model call.
3. **Check input and classify** (in parallel). The input check refuses jailbreaks, role claims, fake notices and requests for non-current text. Tier rules and the fast model each give a risk tier, and the stricter one wins. The scope check refuses anything outside operational procedures and records.
4. **Clarify (new).** If the question is ambiguous in a way that changes the evidence (for example no asset, site or business unit where several apply), ask one short clarifying question and stop. Questions with an emergency cue never take this path.
5. **Retrieve.** Search with the question and up to two rewrites, under RLS for the principal, with current approved versions only (drafts only for roles allowed to see them). Rerank and drop anything below the threshold.
6. **Assess evidence (new).** Decide whether the evidence is sufficient, authoritative and consistent. Record why: top relevance, sections found, overdue or recently revised sources, and declared conflicts between the cited documents.
7. **Route.**
   - Safety-critical: verbatim extracts go to an Authorised Person for release.
   - Insufficient evidence: abstain, and name the escalation route.
   - A declared conflict with no agreed precedence: escalate to the owners of both documents.
   - Otherwise: generate.
8. **Gather records** (if the question needs them). A bounded agent calls read-only record tools, with at most 5 calls and a request-size budget (new; see T13).
9. **Generate.** The answer model drafts the six-part answer. Every claim and step carries a quote and a source ID taken from the evidence.
10. **Validate (new layer).** Named checks run in order (section 4). Each failure leads to a repair (drop the claim), withholding (abstain) or escalation.
11. **Respond and audit.** Return the response. Append audit events for each transition and validation outcome, with masked text only.

### Behaviour when evidence is weak

| Situation | Detected by | Behaviour | Shown to the user |
|---|---|---|---|
| **Missing**: no relevant procedure | Relevance below threshold after reranking | Abstain and escalate | "I couldn't find an approved procedure for this", and who to ask |
| **Stale**: past its review date | Register `review_due` | Answer, with a notice | "Due for review since …" on the source |
| **Superseded, withdrawn or draft** | SQL status filter (they never reach the model); a validator double-checks every cited version | Never cited. A user who asks for one is refused, unless their role sees drafts, and then it's labelled draft. | "Only current approved versions are used" |
| **Recently revised** | Register: a version replaced in the last 12 months | Answer, with a notice | "Replaced an earlier version on …" |
| **Conflicting**: declared in the register | Evidence assessment (new) | Show both sources side by side and escalate to the owners. Never pick a winner unless a precedence rule is agreed (Q1). | "These sources disagree", then both texts, then who decides |
| **Conflicting**: found only by the model | Draft conflict field, checked for two distinct documents | As above, and log it for document control to declare | As above |
| **Unauthorised**: another unit's or restricted document | RLS: it isn't retrievable | Behaves as missing. The existence of restricted documents is never confirmed. | "I couldn't find …" |
| **Insufficient**: partly relevant | Evidence assessment: coverage or the answer's gaps | Answer what is supported and list the gaps under Limitations, or abstain if the core is unsupported | Limitations section |
| **Ambiguous question** | Clarify step (new) | Ask one clarifying question | The question |
| **Safety-critical** | Tier rules or classifier | Verbatim extracts only, released or declined by an Authorised Person | "Waiting for an Authorised Person" |
| **Emergency** | Deterministic screen | Emergency card, no model | Numbers and immediate actions |
| **Provider failure** | Exception, or limit check at start-up | Fixed error response, audited. Nothing decided. | "Couldn't finish; use your procedures as normal" |

## 4. Components: responsibilities and interfaces

| Component | Responsibility | Consumes | Produces |
|---|---|---|---|
| Interface | HTTP and UI. No business rules. | Request, credentials | Rendered response |
| Identity & access | Who is asking and what they may see or release | Credentials | `Principal` |
| Policy | Emergency rules, tiers, scope, escalation routes, prohibited directives | Question, principal | `PolicyDecision` |
| Ingestion | Turn approved sources into indexed, versioned, access-tagged chunks | Source adapter, register | Activated versions, `IngestionReport` |
| Retrieval | Find permitted, current evidence and judge it | Question, principal | `EvidenceAssessment` |
| Records | Read-only lookups of assets, inspections, alarms, work orders and incidents | Asset IDs, words | Records with IDs |
| Generation | Draft the structured answer, or select verbatim extracts | Question, evidence | `AnswerDraft` |
| Validation | Check the draft against evidence and policy | Draft, evidence, principal | `ValidationResult` |
| Orchestration | Run the state machine; pause and resume for approvals | All of the above | `Response` |
| Oversight & audit | Approvals, decisions, append-only events | Workflow events | Audit records |
| Providers | Model access by role, with capability and limit checks | Settings | Chat, embedding and reranking clients |
| Evaluation | Datasets, runs, scoring, gates, reports | Service interface | Report and exit code |

Interfaces, as sketches to agree, not code to merge:

```python
class Principal(Protocol):
    user_id: str
    roles: frozenset[str]
    business_units: frozenset[BusinessUnit]
    releases_for: frozenset[BusinessUnit]  # Authorised Person rights
    sees_drafts: bool


class IdentityProvider(Protocol):
    async def principal(self, request: Request) -> Principal: ...


class Policy(Protocol):
    def screen(self, question: str) -> EmergencyMatch | None: ...
    async def assess(self, question: str, principal: Principal) -> PolicyDecision: ...
    def escalation_route(self, reason: EscalationReason, units: set[BusinessUnit]) -> Route: ...


class Retriever(Protocol):
    async def assess(self, question: str, principal: Principal) -> EvidenceAssessment: ...


class Validator(Protocol):
    name: str
    severity: Severity  # critical -> withhold or escalate

    def check(
        self, draft: AnswerDraft, evidence: EvidenceAssessment, principal: Principal
    ) -> CheckResult: ...


class ModelRegistry(Protocol):
    def chat(self, role: ChatRole) -> BaseChatModel: ...  # FAST or ANSWER
    def embeddings(self) -> Embeddings: ...
    def reranker(self) -> Reranker: ...
    def limits(self) -> ProviderLimits: ...  # checked by doctor


class SourceAdapter(Protocol):
    def documents(self) -> Iterable[SourceDocument]: ...  # bytes + register metadata
```

Validators, in order, with the outcome when one fails:

| Validator | Checks | On failure |
|---|---|---|
| `cited_sources_were_retrieved` | Every source ID is in the evidence set | Withhold |
| `quotes_match_sources` | Every quote matches its source text (existing check) | Drop the claim; withhold if nothing is left |
| `cited_versions_are_current` | Every cited version is approved and current for the principal | Withhold, and raise a critical audit event |
| `claims_have_support` | Every claim and step cites at least one quote | Drop the claim or step |
| `no_prohibited_directives` | No "you are authorised", "proceed without a permit", operating instructions for plant | Withhold, and escalate |
| `conflicts_are_disclosed` | Any declared conflict among the cited documents appears in the response | Escalate |
| `mandatory_notices_present` | Overdue and revision notices are attached | Repair (add them) |
| `structure_complete` | All six parts are present, or explicitly empty | Repair |

## 5. Repository and module structure (P)

The rule is that dependencies point inwards: the interface depends on orchestration, which depends on the domain layers, which depend on providers and storage. Nothing imports `api` or `ui`.

```
src/gigawhat/
  api/            FastAPI routes and schemas                    from api.py
  ui/             Chainlit, via the service interface only       from ui/
  identity/       Principal, IdentityProvider, demo personas     from personas.py
  policy/         emergency rules, tiers, scope, escalation,     from assistant/tiers.py,
                  input rail; rules in YAML                      safety_topics.yaml, rails.py
  ingestion/      source adapters, parsing, metadata checks,     from corpus/
                  chunking, activation
  retrieval/      query analysis, hybrid search, rerank,         from retrieval/
                  evidence assessment
  records/        read-only record tools                         from records/, assistant/evidence.py
  generation/     prompts, rewrite, drafting, verbatim lane      from assistant/answer.py,
                                                                 prompts.py, rewrite.py
  validation/     validators and outcomes                        new, from checks in answer.py
  orchestration/  graph, state, service                          from assistant/graph.py, service.py
  oversight/      approvals and audit                            from assistant/oversight.py
  providers/      model registry, adapters, limits               from models.py
  observability/  logging, metrics, tracing                      from tracing.py
  evaluation/     datasets, checks, runners, reports             unchanged
  storage/        engine, schema, migrations                     from db.py, schema.py, migrations/
  config.py, cli.py
```

The move is mechanical and is done first, with no change in behaviour, so the existing tests and the evaluation prove nothing broke.

## 6. Technology stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language, API | Python 3.12, FastAPI | Existing; typed; the AI libraries are Python-first | — |
| Orchestration | **LangGraph** (keep) | Explicit states, conditional routing, `interrupt()` for human approval, checkpoints in Postgres: exactly brief §4D | Plain Python state machine (fewer dependencies, but approvals and resume would have to be built); LlamaIndex Workflows |
| Integration | LangChain, for model wrappers and the evidence agent only | Saves provider-specific code. Kept thin. | Provider SDKs directly |
| Store | **PostgreSQL 17 + pgvector** (keep) | One store for vectors, full text, RLS, records, audit and checkpoints. RLS is the strongest access control available here. | A separate vector DB (Qdrant, OpenSearch): more to secure and no RLS; Bedrock Knowledge Bases (filtering, not a security boundary) |
| Parsing | Docling (keep) | Good section and table structure from PDFs; runs locally | LlamaParse (hosted, paid); Unstructured |
| Chat, development | **Gemini free tier** (D2, D4), behind the registry: `gemini-3.1-flash-lite` (fast), `gemini-3.5-flash-lite` (answer) | Free; a full evaluation uses about half of each model's daily quota | Groq free (8,000 tokens a minute: fails); offline Ollama (free, slow) |
| Chat, paid | `gpt-oss-20b` on Groq's Dev tier | Cheapest paid option that fits; the same weights as the offline profile | OpenAI small models (need retuning) |
| Embeddings | OpenAI `text-embedding-3-small` | Already indexed; about a cent for the corpus | Gemini embeddings (free; re-index needed); local Qwen3 (offline profile) |
| Reranker | Local `bge-reranker-v2-m3` (development); Cohere when hosted | The 0.2 and 0.3 thresholds were tuned on bge; free | Cohere only (needs a paid key); none (worse retrieval) |
| Personal data | Presidio + spaCy (keep) | Runs locally, before any model | Provider-side redaction (data has already left) |
| Input rail | NeMo Guardrails (kept, D1) | Existing and tested | Fold into the tier classifier: one call fewer |
| Tracing | LangSmith, optional and cloud only; EU by default, US for the demo (D5) | Native to LangChain; free developer plan | Langfuse (removed) |
| Evaluation | Own checks and gates; on the cloud profile run as LangSmith experiments (`aevaluate`, a dataset synced from the YAML, gates as summary scores); DeepEval (kept, D1) | Deterministic gates matter more than judge scores (brief §4F); experiments make runs comparable | promptfoo; Ragas |
| UI | Chainlit for the demo | Existing | A mobile-first web UI for field use, once a pilot workflow is chosen (Q6) |
| Hosting | Undecided (D3, Q4) | Must be cheap and suit the data-residency answer | A small VM; a PaaS free or low tier |

## 7. Threat model and failure modes

| ID | Threat or failure | How | Impact | Controls: today → proposed | Residual |
|---|---|---|---|---|---|
| T1 | Prompt injection in the question | "Ignore your rules", fake overrides, claimed roles | Bypassing tiers or access | Input rail, tiers, no side-effecting tools, RLS → policy module; red-team cases per rule | Medium. R012, R017 and R018 passed the input rail and were stopped further on. |
| T2 | Injection hidden in documents or records | Text in a source that reads like instructions | The model follows the source instead of the policy | Only documents in the register are ingested → sources wrapped as data in prompts; `no_prohibited_directives`; injection fixtures in the corpus | Medium |
| T3 | Unauthorised disclosure | Asking about another unit's or a restricted document | A confidentiality breach | RLS by unit → document-level entries; `cited_versions_are_current` also checks access; new gate G6 | Low for units; medium until document-level access exists |
| T4 | Fabricated procedure or citation | Model invention | False authority | Quote verification; IDs come from the database → `cited_sources_were_retrieved`; gate G7 | Low |
| T5 | Citing a superseded, draft or withdrawn version | Stale index or model error | Unsafe work | SQL status filter; gate 1 → a validator double-checks | Low |
| T6 | A model makes a safety-critical decision | Misclassified tier | Unsafe work | Rules plus classifier, stricter wins; verbatim lane; Authorised Person release; gate 3 | Low to medium: depends on how well the rules cover phrasings |
| T7 | Missed emergency | Unusual phrasing | Delay in an emergency | Deterministic screen; gate 2 → more phrasing cases | Low to medium |
| T8 | Contradiction silently resolved | The model picks one source | Wrong procedure followed | The model reports conflicts → conflicts declared in the register; `conflicts_are_disclosed`; gate G8 | Medium until conflicts are declared |
| T9 | Personal data reaches providers or logs | Typed into a question or a note | A data-protection breach | Presidio before graph state, models and audit → redacted structured logs; masking test set | Medium (known detection gaps) |
| T10 | Approval forged or bypassed | Anyone can pick the Authorised Person persona in the demo | An unauthorised release | Labelled as a demo → identity provider and the authorisation register (Q3) | **High in the demo**; must be fixed before any pilot |
| T11 | Audit lost or altered | Failure mid-workflow; tampering | No accountability | Append-only table; failures audited → events per transition | Low |
| T12 | Provider limit, quota or outage | **Seen 14 Oct: Groq free plan, 413** | No answer | Fixed error response, audited → start-up limit check, request-size budget for the evidence agent, a fallback provider per role, retries with backoff | Medium |
| T13 | Costs run away | Public demo, scripted traffic | Spend | Per-visitor limit; token caps → cost metric per provider; daily budget; free tiers in development (D2) | Low |
| T14 | Free-tier data use | Gemini free tier may use prompts to improve products | Disclosure of real data | Fictional data only → paid terms with no training on data before any real data (Q5) | Accepted for the demo only |
| T15 | Over-reliance (automation bias) | Staff treat suggestions as instructions | Unsafe work | Separate "the procedure says" from "suggested next step"; state that it is not an authorisation; pilot measures | Medium |
| T16 | Dependency compromise | Malicious package | Anything | `uv.lock` with hashes; CI | Low to medium |

## 8. Evaluation plan

### Three levels

| Level | Dataset | Measures |
|---|---|---|
| Retrieval (new) | Each golden question labelled with the document and section that answer it | Recall at 5 and at 10, mean reciprocal rank, share of results that are current approved versions |
| Generation and validation | Golden answers, plus adversarial drafts fed straight to the validators | Citation validity, quote-match rate, share of claims supported, structure complete, validator precision |
| End-to-end | Golden (60) and red-team (25), extended | Behaviour, tier, required citations, notices, abstention and escalation correctness, latency, cost |

### The brief's twelve scenarios against today's cases

| # | Scenario | Existing cases | To add |
|---|---|---|---|
| 1 | One authoritative source | G002 and most answer cases | — |
| 2 | Needs several documents | Records-plus-procedure cases such as G014 (T-104 acetylene trend; must cite PR-ELEC-044) | 3 to 5 cases needing two procedures |
| 3 | Ambiguous: needs clarification | **None** | 8 cases, e.g. "What's the isolation procedure?" with no asset or voltage |
| 4 | Relevant procedure missing | 9 abstain cases | Check that each names an escalation route |
| 5 | Conflicting guidance | G026 (PR-CORP-004 against PR-ELEC-001), G036 | Declare the conflict in the register; add 2 cases |
| 6 | Expired or superseded | Superseded PR-GAS-031 v2, withdrawn PR-GAS-071, overdue reviews (G010) | — |
| 7 | Restricted information | R017, R018 (other unit) | Document-level restricted cases, once access is per document |
| 8 | Misleading assumption | R012 (pasted "approved v4" with a false 1.5 m height) | 4 golden cases with a false premise |
| 9 | Adversarial override | R001 to R013 | Injection inside a document (T2) |
| 10 | Safety-critical, no autonomous decision | 22 safety-critical cases | — |
| 11 | Should say it doesn't know | Abstain cases | Separate "doesn't know" from "may not see" |
| 12 | Human review of the next step | The pending and release flow | Escalation cases for contradiction and out-of-scope questions |

### Hard gates

The five existing gates stay. Three are added:

- **G6. No unauthorised disclosure:** no cited or quoted text from outside the principal's access.
- **G7. No fabricated citation:** every cited ID was retrieved and every quote matches its source.
- **G8. Every declared conflict among the cited sources is disclosed or escalated.**

### Proposed targets

To be agreed with the safety team (Q9):

| Measure | Proposed | Offline baseline (10 Oct) |
|---|---|---|
| Behaviour as expected | ≥ 90% | 85% |
| Tier as expected | ≥ 90% | 89% |
| Required document cited | ≥ 85% | 66% |
| Red-team refused | ≥ 95% | 86% |
| Notices shown | ≥ 90% | 44% |
| Retrieval recall at 5 | ≥ 90% | not measured |
| Clarification when expected | ≥ 80% | not measured |
| Median latency on cloud | < 10 s | 11.3 s offline |

### How it runs

- **CI:** every push runs the unit and integration tests with scripted models, at no cost.
- **Real-model evaluation:** run by hand on the free tier. `--limit` gives quick checks, and a full run fits in the daily quota (to confirm for Gemini).
- **Releases:** a release needs a full run with all gates passing, and the report goes in `evals/reports/`.

## 9. Roadmap and acceptance criteria

| Phase | Work | Accepted when |
|---|---|---|
| **1. Discovery and architecture** (now) | This document; answers to Q1–Q11 | The owner agrees the design; each open question is answered or deferred with an owner |
| **2a. Providers** (built 14 Oct) | Model registry by role; Gemini adapter; limit check in `doctor`; request-size budget for the evidence agent; LangSmith tracing and experiments | `doctor` reports provider limits; the full 85-case evaluation completes on the free tier; five gates pass |
| **2b. Layer split** (built 14 Oct) | The module moves in section 5; validation extracted into named validators; structured JSON logging | No change in behaviour: all tests pass and evaluation results are within run-to-run noise |
| **2c. Brief behaviours** | Six-part answer; clarify outcome; escalation routes; evidence assessment | The new clarification and escalation cases pass; the UI shows each part; G7 passes |
| **3. Hardening** | Conflicts declared in the register and their validator; document-level access; retrieval dataset and metrics; injection fixtures in documents; cost metrics | All eight gates pass; the targets in section 8 are met or have accepted exceptions |
| **4. Pilot** | Hosting (Q4); identity provider (Q3); Authorised Person notifications; one chosen workflow (Q6); feedback capture | Agreed with stakeholders; T10 closed |
| **5. Production readiness** | Ownership, incident response, change control, model updates, document lifecycle, ongoing evaluation | Agreed operational criteria |

## 10. Questions that must be answered before Phase 2

| ID | Question | Why it matters | Default if unanswered |
|---|---|---|---|
| Q1 | When two approved documents conflict, is there a precedence rule (for example, company-wide safety rules over unit procedures), or must every conflict go to a human? Who declares conflicts? | Decides whether G8 escalates or answers | Always escalate to both owners |
| Q2 | Who is the human for each escalation reason (ambiguous, contradictory, out of scope, missing procedure), and through what channel? | Escalation must name a real route | The document owner's role, shown as text |
| Q3 | Which identity provider, and where do Authorised Person rights come from? | Closes T10 | Demo personas, clearly labelled |
| Q4 | Where will it be hosted, and are there data-residency limits? | Provider and hosting choice | A small, low-cost VM; residency documented |
| Q5 | Which model providers are acceptable once real data is involved? | The Gemini free tier is for fictional data only | Paid tiers with no training on data |
| Q6 | Which single workflow should the pilot support (control-room lookups, planned-work job packs, reactive field work)? | Decides the UI and offline needs | Control-room lookups (desk, online) |
| Q7 | When should it ask for clarification instead of answering with stated assumptions? At most one clarifying question? | Defines scenario 3 behaviour | One question, only when the evidence would differ |
| Q8 | How long should audit events, logs and traces be kept? | Data protection | Audit 12 months; logs 30 days; traces 14 days |
| Q9 | Are the proposed targets and the three new gates acceptable? | Acceptance criteria | As proposed |
| Q10 | Is offline field use needed for the pilot? | Architecture of the client | No |
| Q11 | Keep the offline (Ollama) profile long term, or only as a development stand-in? | Maintenance cost | Development stand-in |
