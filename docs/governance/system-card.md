# GigaWhat system card

| | |
|---|---|
| System | GigaWhat, an assistant for operational staff at Harrowmere Energy |
| Status | Reference implementation run as a demo. Harrowmere Energy, its procedures and its records are fictional. |
| Written against | Commit `3e8cb02` plus the follow-up fixes made on 10 October 2026 |
| Owner | Not yet named. A real deployment needs a named system owner (see [README](README.md)). |

This card says what GigaWhat is for, what it must not be used for, how it produces answers and where it is known to fall short. Every statement points at the code that makes it true. Where the code does not do something, the card says so.

## 1. Intended purpose

GigaWhat helps operational staff at a UK gas and electricity network operator to:

1. find the approved, current procedure for a job, asset, site and role;
2. see what that procedure says, with a citation to the document, version and section;
3. summarise evidence from operational records (assets, inspections, alarms, work orders, incidents), citing each record;
4. get suggested next steps, each tied to a cited source;
5. send safety-critical procedure extracts to an Authorised Person, who releases or declines them.

People make every decision. GigaWhat is advisory. It reads documents and records; it cannot change anything.

## 2. Intended users

The demo offers six personas. Each maps to the role and business-unit access a real user would get from single sign-on (`src/gigawhat/personas.py`).

| Persona | Role | Sees | Can do |
|---|---|---|---|
| Gas field engineer | First Call Operative | Gas and company-wide (`shared`) documents and records | Ask; raise approval requests |
| Electricity control room | Control Engineer | Electricity and `shared` | Ask; raise approval requests |
| Authorised Person (Gas) | Authorised Person (Gas) | Gas and `shared` | Ask; release or decline gas requests |
| Authorised Person (HV) | Authorised Person (HV) | Electricity and `shared` | Ask; release or decline electricity requests |
| Document controller | Document controller | All units. The register view lists drafts. | Ask; view the register |
| Auditor | Auditor | All units | Ask; view this browser's audit trail |

In the demo, visitors pick a persona with no sign-in. Nothing checks that a visitor really holds the role. See [human-oversight.md](human-oversight.md) for what production would need.

## 3. Out of scope

GigaWhat must not be used for any of the following. The design keeps them out of reach; the people using it must keep them out of practice.

- **It does not make or approve safety-critical decisions.** It never issues, authorises or closes a permit-to-work, sanction-for-test or isolation. A "release" in GigaWhat is an Authorised Person's sign-off on procedure extracts. It is not a permit.
- **It does not connect to plant, SCADA or any operational technology (OT).** It has no tools that switch, open, close, set or control equipment. The evidence tools run fixed, read-only SQL against copies of records in its own database (`src/gigawhat/assistant/evidence.py`). Requests to operate equipment are refused by the input guardrail (`INPUT_POLICY` in `src/gigawhat/assistant/prompts.py`; red-team cases R008 to R010).
- **It is not an emergency service.** If a question describes a current danger, it shows fixed text with 999, the National Gas Emergency Service number 0800 111 999 and the power-cut number 105 (`EMERGENCY_TEXT` in `src/gigawhat/assistant/responses.py`). It does not alert anyone, dispatch anyone or log an emergency with any other system.
- It does not write its own steps for safety-critical work. It quotes the approved procedure word for word.
- It does not use draft, withdrawn or superseded documents to answer questions about current practice.
- It is not a substitute for competence, training, the permit-to-work system or the full procedure.
- It is not for real operational work in this demo form. The data is invented.

## 4. Profiles and models

`GIGAWHAT_PROFILE` chooses where models run (`src/gigawhat/config.py`, `src/gigawhat/models.py`). Each profile has its own database because the two embedding models produce different vectors.

| Job | `cloud` profile (default; the hosted demo) | `offline` profile |
|---|---|---|
| Safety-tier classifier and input guardrail ("fast model") | Claude Opus 5.5 (`claude-opus-5-5`), effort `low`, up to 2,048 output tokens | `gpt-oss:20b` on Ollama, reasoning `low`, temperature 0 |
| Evidence gathering and cited answers ("answer model") | Claude Opus 5.5 (`claude-opus-5-5`), effort `high`, up to 16,000 output tokens | `gpt-oss:20b` on Ollama, reasoning `medium`, temperature 0 |
| Refusal handling | Anthropic server-side fallback beta `server-side-fallback-2026-07-01` with `fallbacks: default`: a refused request is retried server-side on a model Anthropic chooses by refusal category | None |
| Embeddings | Cohere `embed-v4.0`, 1,536 dimensions | `qwen3-embedding:0.6b` on Ollama, 1,024 dimensions, with a task instruction on queries only |
| Reranker | Cohere `rerank-v3.5` | `BAAI/bge-reranker-v2-m3`, run locally with sentence-transformers |
| Personal-data detection | Presidio with spaCy `en_core_web_md` 3.8.0, run locally | Same |
| Document parsing (ingestion only) | Docling, OCR switched off | Same |
| Chunk boundaries (ingestion only) | Tokenizer `Qwen/Qwen3-Embedding-0.6B`, 512 tokens per chunk, so both profiles split documents identically | Same |
| Evaluation judge | The answer model above | The answer model above |

The same chat model does every model task within a profile. Each audit event records the chat, embedding and reranker model names (`models` column). It records the configured chat model, not the model that served a fallback.

The hosted image (`Dockerfile`) is cloud-only. It leaves out Docling and PyTorch, which are optional extras (`ingest`, `offline`) in `pyproject.toml`.

## 5. Data sources

| Source | What | Where |
|---|---|---|
| Document register | 33 documents: 26 fictional Harrowmere procedures (28 versions, including superseded, draft and withdrawn ones) and 7 public HSE publications (HSG250, HSG253, HSG85, HSR25, L80, L122, L138). The register, not the file, decides which version is current. | `data/corpus/register.yaml`, `data/corpus/procedures/` |
| HSE guidance | Downloaded from hse.gov.uk by `gigawhat data fetch-hse` and checked against the SHA-256 recorded for it in the register (`source_sha256`); a changed file is refused. Not committed or redistributed. | `data/raw/hse/` |
| Operational records | Fictional sites, assets, work orders, inspections, incidents and alarms. People are identified by role only. | `data/records/` |
| Questions | Typed by users. They may contain personal data, which is masked first (section 6, step 1). | Not stored unmasked |

`data/README.md` lists the deliberate test cases planted in the data: superseded versions, a draft, a withdrawn procedure, an overdue review and two pairs of conflicting procedures.

## 6. How an answer is produced

The workflow is a LangGraph graph (`src/gigawhat/assistant/graph.py`). Every path from question to answer passes through the safety gate.

1. **Mask personal data.** Presidio replaces names, addresses, postcodes, phone numbers and other identifiers with placeholders before the question enters graph state, which is saved to Postgres (`Assistant.ask` in `src/gigawhat/assistant/service.py`).
2. **Screen for emergencies with fixed rules.** Regular expressions in `src/gigawhat/assistant/safety_topics.yaml` run first. If one matches, the emergency card is shown without asking any model.
3. **Check the input and classify the tier, in parallel.** The NeMo Guardrails input rail asks the fast model whether to block the message (`src/gigawhat/assistant/rails.py`). The fast model also classifies the safety tier (`classify_with_model` in `src/gigawhat/assistant/tiers.py`).
4. **Take the stricter tier.** The rules set a floor; the classifier can only raise it (`stricter` in `tiers.py`). An emergency beats a blocked input.
5. **Route.**
   - Emergency: fixed emergency card.
   - Blocked input: fixed refusal.
   - Otherwise: retrieve.
6. **Retrieve.** The fast model rewrites the question into up to two search queries (`rewrite_queries` in `src/gigawhat/assistant/rewrite.py`); if that call fails, the question alone is used. Hybrid keyword and vector search runs, for the question and each rewrite, inside Postgres against the `current_chunks` view, as the restricted reader role, under row-level security for the persona's business units (`src/gigawhat/retrieval/search.py`, migration `0004_access_control.py`). Up to 24 candidates per query are merged and reranked against the original question, so a rewrite can add candidates but never decides what is relevant. The best hit per section is kept, and the top 6 sections are expanded to their full text.
7. **Abstain if the evidence is thin.** Only passages scoring at least 0.2 with the reranker (`MIN_RELEVANCE`) count. If none do and the question is not about an asset, its history or document control, GigaWhat says it found no approved procedure or record that answers the question and points to the Authorised Person or document controller. A records question goes on to the record tools even when no procedure matches, and abstains there if they find nothing to cite.
8. **Safety-critical questions (strict mode).** Code copies up to two sections of approved procedures that score at least 0.3 with the reranker (`STRICT_MIN_RELEVANCE`), word for word (`strict_extracts` and `render_extracts` in `responses.py`). HSE guidance alone is not enough, and sections such as revision history or references are skipped. No model writes any text. An approval request carrying the extract goes to the Authorised Persons of the unit that owns the procedure (company-wide procedures go to the requester's unit). The requester sees only which sections are waiting, not their text. The graph pauses at LangGraph's `interrupt()` until an Authorised Person releases or declines the request, or it expires after 24 hours.
9. **Other questions.** If the question names an asset, asks about history or asks about document control (current, superseded or withdrawn versions, overdue reviews), a small agent makes up to five calls to six read-only record tools (`evidence.py`): asset details, inspections, alarms with a per-code count, work orders, incident search and the document register. The answer model then fills a fixed schema: claims, next steps, conflicts and gaps, each citing source IDs and quoting the first cited source.
10. **Verify in code.** `verify` in `src/gigawhat/assistant/answer.py` drops any claim with no citation, an unknown source or a quote not found in the cited source. Quotes of 40 characters or more may differ slightly from the source (at least 85% must be one unbroken match, to allow for PDF hyphenation and punctuation), but every number in a quote must appear in the source. It drops next steps that cite unknown sources, conflicts that do not cite two different documents, and a summary that contains numbers not found in a kept claim. If no claim survives, GigaWhat abstains.
11. **Render.** Claims with citations, suggested next steps (marked when the model says an Authorised Person is needed), any conflict with a referral to the document owners, the parts of the question the sources do not cover, a notice for each cited document past its review date, a notice for each cited document that replaced an earlier version in the last 12 months (so nobody works from an old printed copy), a safety banner for safety-relevant answers, and a closing line: "Written by AI from approved documents; check the cited sources."
12. **Audit.** Every outcome is written to the append-only `audit_events` table with the masked question, tier, guardrail results, sources, response, verification drops, model names, prompt version and latency. If a model or API call fails anywhere in the graph, an event of type `error` is written instead and the user gets a fixed service-error message (`Assistant.ask` in `service.py`).

What the user sees, by outcome (`ResponseKind` in `responses.py`):

| Outcome | Text written by | Notes |
|---|---|---|
| `answer` | Model, checked in code | Citations, notices, "Not covered by the sources", AI note, Helpful / Not helpful buttons |
| `pending` | Fixed text listing the section labels | Waiting for an Authorised Person; no procedure text |
| `released` | Copied text plus "Released by ..." and the Authorised Person's note | |
| `declined` | Fixed text plus the Authorised Person's note | No extract and no sources |
| `emergency` | Fixed text | 999, 0800 111 999, 105 |
| `refusal` | Fixed text | |
| `abstain` | Fixed text | |
| `paused` | Fixed text | Only when `GIGAWHAT_PAUSED` is true |
| `error` | Fixed text | A model or API call failed; nothing was decided |

## 7. Known limitations and failure modes

These are honest limits of the current build. The [risk register](risk-register.md) gives the controls and residual risk for each.

**Speed and model size**

- On the offline profile, answers take about a minute on a laptop (README). The cloud profile is much faster.
- Small local models misclassify more. In the first two full offline runs the classifier rated informal safety-critical questions ("can the van stay parked inside it?", "how fast can I ramp?") as safety-relevant, so the model wrote answers. The fixed rules were widened after each run, and the third run passed every release gate ([evaluation-report.md](evaluation-report.md)). The rules protect only the phrasings they match, so a new phrasing can still get through when the classifier underrates it.

**What the checks do not catch**

- The summary sentence is checked only for numbers that do not appear in a kept claim. Its wording is not otherwise checked.
- A claim's own wording is not compared with its quote. The check is that the quote appears, in order, in the first cited source. A claim can therefore overstate what its quote says.
- Next steps are checked only for citing sources that exist. Their wording and the "needs an Authorised Person" flag are the model's judgement.
- Conflicts between procedures are reported only if the model notices them. Strict mode never flags conflicts.

**Documents and retrieval**

- Tables are linearised into text by Docling when documents are loaded. Readings and limits held in tables can be harder to find and harder to read in an extract.
- Keyword search uses one precise term per question (an asset ID, an expanded abbreviation or a rating). Everything else relies on vector search and the reranker.
- Strict mode quotes at most two sections. They may not be the right ones, and they are never the whole procedure. The preface tells the user to work to the full procedure and their permit.
- The relevance thresholds (0.2 for an answer, 0.3 for a strict extract) were set on a small fictional corpus with the offline reranker (bge-reranker-v2-m3). Cohere's scores are distributed differently, so both must be checked with the evaluation on the cloud profile before they are relied on there. No single threshold separates every genuine question from every near miss: in the evaluation, a chatty but genuine safety-critical question scored its right section at 0.35 and a near miss scored 0.29.
- Record tools have fixed windows: the latest 6 inspections, alarms in the 120 days before the newest alarm, open work orders plus the last 3 completed, and up to 5 incidents. Records are gathered only when the question names an asset or uses words such as "alarm", "history", "trend", "current", "superseded" or "overdue" (`RECORDS_INTENT` in `evidence.py`).
- Overdue notices use the server's date.

**Safety routing and approvals**

- Emergency rules are English regular expressions. Other phrasings depend on the model. If the model is unavailable and the rules do not match, the user sees the service-error message, not the emergency card.
- Separation of duties compares personas, not people. A request made by an Authorised Person persona can only be released by a different persona of the same unit, so in the demo it cannot be released and expires after 24 hours.
- Nothing checks that an Authorised Person opened the full extract before releasing it.

**Operation**

- Personas are chosen, not authenticated. Single sign-on is not built.
- The pause switch is read at start-up, so it needs a restart, and paused replies are not audited.
- Personal-data masking has known gaps ([data-protection.md](data-protection.md), section 5).
- Questions and answers are in English only.

## 8. Evaluation

The golden set (60 cases) and red-team set (25 cases), the five release gates and the quality targets are described in [evaluation-report.md](evaluation-report.md). The unit and integration test suite (337 tests on 10 October 2026) runs in CI on every push and pull request.

## 9. Reporting a problem

| Problem | What to do |
|---|---|
| A safety concern about an answer or extract | Stop. Do not act on it. Work to your procedure and speak to your Authorised Person. Then report it as below. |
| GigaWhat is giving unsafe or wrong answers to many people | The operations team sets `GIGAWHAT_PAUSED=true` and restarts the app ([human-oversight.md](human-oversight.md), section 11). |
| An answer was unhelpful or wrong | Press **Not helpful** under the answer. This records the thread ID, persona and browser ID in the `feedback` table. It does not record a reason. |
| Anything else in the demo | Open an issue on the project's GitHub repository. Give the time, the persona, and the approval ID or thread ID if you have one. Do not include personal data. The Auditor persona and `/api/audit` show this browser's audit trail. |

A real deployment needs a named owner, an incident route into the company's safety management system and a target time to respond.
