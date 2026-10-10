# Data protection impact assessment (DPIA-style)

| | |
|---|---|
| Status | Draft prepared by engineering for the demo. It has not been reviewed by a data protection officer (DPO) and no consultation has taken place. |
| Written against | Commit `3e8cb02` plus the follow-up fixes made on 10 October 2026 |
| Controller | For the demo: whoever operates the hosted instance. For a real deployment: the utility. |
| Audience | Data protection officer, security, engineering |

This document follows the shape the ICO describes for a DPIA: the nature, scope, context and purposes of the processing; necessity and proportionality; risks to individuals; and measures to reduce them. It is not legal advice. Harrowmere Energy, its staff and its customers are fictional, and the demo is not meant to process real personal data. It still can, because anyone with the link can type anything into a question.

## 1. Why a DPIA

UK GDPR requires a DPIA where processing is likely to result in a high risk to individuals. The ICO lists the use of innovative technology, in combination with other criteria, as one of the triggers. A real deployment of GigaWhat would use large language models on free text that can contain customers' details during gas escapes and other incidents, and some of that processing goes to third-party processors outside the UK. A DPIA is the sensible default. The ICO notes that its DPIA and AI guidance is under review following the Data (Use and Access) Act 2025.

## 2. Description of the processing

| | |
|---|---|
| Purpose | Help operational staff find approved procedures, summarise operational records and route safety-critical extracts to an Authorised Person. |
| Nature | Free-text questions are masked for personal data, then classified, used to search documents and records, and answered by a language model or by copied procedure text. Every outcome is logged. |
| Scope | Questions, answers, approval decisions, feedback, a random browser ID, and in production the identity of staff users. |
| Context | Staff at a gas and electricity network operator, often in the field, sometimes during incidents involving members of the public. |
| Data subjects | Customers and members of the public mentioned in questions; staff users; Authorised Persons. |

## 3. Data flows

The order in which data moves for one question on the cloud profile. Step numbers match `Assistant.ask` in `src/gigawhat/assistant/service.py` and the graph in `src/gigawhat/assistant/graph.py`.

| # | From | To | Data | Personal data? | Leaves the host? |
|---|---|---|---|---|---|
| 1 | Browser | App (Chainlit over HTTPS via Caddy) | Question as typed; `gw_visitor` cookie; chosen persona | Yes, possibly: whatever the user typed; browser ID | No (arrives at host) |
| 2 | App | App memory | Uvicorn access log line with client IP address and path, written to the container log | IP address | No |
| 3 | App | Presidio and spaCy, in process | Question as typed | Yes | No |
| 4 | App | Graph state, saved to Postgres checkpoint tables | **Masked** question, persona, browser ID | Browser ID; masking misses | No |
| 5 | App | Anthropic API (input rail, tier classifier and query rewriting) | Masked question with the guardrail, tier and rewrite prompts | Masking misses only | **Yes** |
| 6 | App | Cohere API (embedding) | Masked question and up to two rewrites of it | Masking misses only | **Yes** |
| 7 | App | Postgres as `gigawhat_reader` | Search query; returns document chunks | No | No |
| 8 | App | Cohere API (rerank) | Masked question and up to 24 candidate passages | Masking misses only | **Yes** |
| 9 | App | Postgres as `gigawhat_reader` (evidence tools, if triggered) | Asset IDs and search words; returns records | No (records name roles only) | No |
| 10 | App | Anthropic API (evidence agent and answer) | Masked question, sources, records, prompts | Masking misses only | **Yes** |
| 11 | App | Postgres `approvals` (safety-critical only) | Masked question, extract, citations, requester browser ID and persona | Browser ID | No |
| 12 | App | Postgres `audit_events` | Masked question, entity types found, tier, sources, response, model names, prompt version, latency, browser ID, persona. If a model or API call fails, an `error` event with the masked question and the error's class name. | Browser ID; masking misses | No |
| 13 | App | Langfuse Cloud EU (cloud profile only, and only if both Langfuse keys are set) | Trace of every model call, tool call and graph step: masked question, prompts, sources, records, outputs; persona tag; thread ID | Masking misses only | **Yes** |
| 14 | Authorised Person's browser | `approvals`, graph state, `audit_events` | Decision, decider browser ID and persona, and a required free-text note, **masked** before storage (`Assistant.decide`) | Browser ID; masking misses in the note | No |
| 15 | Browser | `feedback` | Thread ID, browser ID, persona, helpful yes or no | Browser ID | No |
| 16 | App | NVIDIA telemetry endpoint (NeMo Guardrails default) | Nothing: usage statistics are switched off by `NEMO_GUARDRAILS_NO_USAGE_STATS=1`, set in `src/gigawhat/assistant/rails.py` and in the `Dockerfile`. The image also sets `HF_HUB_DISABLE_TELEMETRY=1`, and DeepEval's telemetry is off (`src/gigawhat/evaluation/judge.py`). | No | No |

On the **offline** profile, steps 5, 6, 8 and 10 go to Ollama and a local reranker on the same machine, and step 13 never happens: tracing is not enabled on the offline profile whatever keys are set (`create_tracer` in `src/gigawhat/tracing.py`; `tests/test_tracing.py`). The first run downloads the chunking tokenizer and reranker from Hugging Face; `.env.example` suggests `HF_HUB_OFFLINE=1` afterwards.

## 4. Personal data categories

| Category | Source | Likely in the demo? | In production |
|---|---|---|---|
| Customer and public names, house numbers and streets, postcodes, phone numbers, email addresses | Typed into questions, for example when relaying a gas escape report | Possible; the red-team set uses invented examples (R022 to R025) | Likely |
| Other identifiers: meter point numbers (MPRN, MPAN), account numbers, vehicle registrations | Typed into questions | Possible | Likely; **not detected** today |
| Health and vulnerability information ("resident is on oxygen", "someone has collapsed") | Typed into questions | Possible | Likely, and may be special category data; **not detected** today |
| Browser ID (`gw_visitor`, random, 30 days) | Set by `src/gigawhat/api.py` | Yes | Replaced or joined by staff identity |
| IP address | Uvicorn access log | Yes | Yes |
| Staff identity (name, email, groups) | Single sign-on | No (not built) | Yes, in approvals and audit |
| Free text in release and decline notes (masked before storage) | Typed by Authorised Persons | Possible | Likely |
| Personal data inside operational records | Records | No: the fictional records identify people by role only | Possible in real incident reports, and sent to the model as evidence |

## 5. Masking with Presidio

`src/gigawhat/assistant/pii.py` runs Presidio locally with the spaCy `en_core_web_md` model, before the question reaches graph state, any model, Langfuse or the audit trail. Authorised Persons' release and decline notes are masked the same way before they are stored (`Assistant.decide` in `service.py`; `tests/test_graph.py::test_decision_note_is_masked_before_it_is_stored`).

| Detected | Replaced with |
|---|---|
| Person names (spaCy named-entity recognition) | `[name]` |
| UK phone numbers (Presidio's recogniser limited to GB, plus a backup pattern for numbers the phone library rejects) | `[phone]` |
| Email addresses | `[email]` |
| House number and street, for 13 street types (Road, Street, Lane, Avenue, Close, Way, Drive, Crescent, Gardens, Place, Terrace, Court, Grove), and "number 14 ... Road" | `[address]` |
| UK postcodes | `[postcode]` |
| NHS numbers, card numbers, IBANs, IP addresses (Presidio built-ins) | `[NHS number]`, `[card number]`, `[bank account]`, `[IP address]` |

Settings that matter: a score threshold of 0.35 (Presidio scores UK phone numbers at 0.4); asset and document IDs such as `FDR-ASH-07` and `PR-GAS-031` are never treated as personal data; spans with no digits that contain a company term (Harrowmere, Kingsmead, Ashford, Vale, Mill Lane, job titles and so on) are allowed through; the gas emergency number 0800 111 999 is allowed through. Only the entity types found, not the values, go into the audit record.

Tests: `tests/test_pii.py` (names, house number and street, "number 22 Vale Road", postcode, mobile, landline, email, entity types, and six company phrases left alone). The evaluation gate "No personal data repeated" checks that personal data in red-team questions does not appear in the response text.

Known gaps:

- Street types outside the list of 13 (for example Hill, Row, Rise, Square, Mews, Park) and house names without numbers.
- Meter point numbers, customer account numbers, vehicle registrations and dates of birth.
- Health, disability and vulnerability details.
- Names written in lower case or not recognised by the spaCy model.
- A surname or place name that matches a company term (for example "Mrs Vale") is allowed through.
- Any future free-text field must be masked too (`feedback.comment` exists but is unused).
- The gate checks only the response text, not what was sent to processors.

## 6. What is stored where, and for how long

There is no retention or deletion process in the code today. Everything below is kept until someone removes it by hand.

| Store | Contents | Personal data | Retention today | Suggested production retention (for the DPO and safety team to decide) |
|---|---|---|---|---|
| `audit_events` (Postgres) | One row per outcome: masked question, entity types, tier, guardrail results, decision and note, sources, response, verification drops, model names, prompt version, latency, browser ID, persona | Browser ID or staff identity; masking misses; decision notes | Forever. A trigger refuses UPDATE, DELETE and TRUNCATE, so ordinary deletion is impossible by design. | Align with safety-record retention for released safety-critical decisions. Keep all events for at least 6 months (the minimum the EU AI Act sets for logs held by deployers of high-risk systems, used here as a benchmark). Purge older routine events through a controlled, recorded process, for example by monthly partitions dropped under a separate privileged role. |
| `approvals` | Masked question, extract, citations, requester and decider browser IDs and personas, masked decision note, times | As above | Forever. Pending requests stop being decidable after 24 hours (`APPROVAL_TTL`) but the rows stay. | Same as the audit events they relate to |
| LangGraph checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, created by `AsyncPostgresSaver.setup()`) | Full graph state per question: masked question, retrieved passages, records, response, decision | As above | Forever | Delete 30 days after a thread finishes. The audit trail holds the lasting record. |
| `feedback` | Thread ID, browser ID, persona, helpful yes or no | Browser ID | Forever | 12 months |
| Langfuse Cloud EU (cloud profile, if enabled) | Traces of every step | Masking misses | Set by the Langfuse plan | 30 to 90 days; or self-host |
| Container logs on the host | Uvicorn access lines with IP addresses; error traces | IP addresses | Docker caps each container log at 3 files of 10 MB (`user_data.sh.tftpl`) | 30 days in a managed log store |
| EBS snapshots (lean host) | Whole root volume, including Postgres | Everything above | 7 daily snapshots (`infra/terraform/lean/backup.tf`) | Match the database retention; deletion takes effect only when the last snapshot holding the data expires |
| Seed bucket (S3) | Documents and records dump | No | Deleted after 30 days (`infra/terraform/lean/storage.tf`) | No change |
| Chainlit `.files/<session>/` | Source passages shown in the side panel, for the session | No | Normally removed when the session ends | No change |
| Browser | `gw_visitor` cookie: random ID, HttpOnly, SameSite Lax, Secure over HTTPS | Browser ID | 30 days | Replaced by the sign-on session |
| Evaluation reports (`evals/reports/`, GitHub Actions artefacts) | Fictional evaluation questions and results | No | Kept in Git or as artefacts | No change |

The append-only design and the right to erasure pull in different directions. Masking before storage reduces the conflict but does not remove it, because masking can miss things. The DPO needs to decide how an erasure request for data in an audit record will be handled.

## 7. Processors and recipients, by profile

| Recipient | Role | Profile | What it receives | Location and retention, as published |
|---|---|---|---|---|
| Anthropic (Claude API) | Processor | cloud | Masked questions, prompts, retrieved sources, records, model outputs | Inference geography defaults to `global` (may run in any available geography); the code does not set `inference_geo`. The only workspace data-at-rest geography offered is `us`. Anthropic states conversation content is not retained by default and never used for training without permission, except for designated "Covered Models" (Claude Opus 5.5 is not one), legal requirements, or content flagged by trust and safety systems (up to 2 years). |
| Cohere (Embed and Rerank API) | Processor | cloud | Masked questions; candidate passages for reranking | Cohere's data usage policy says logged prompts and generations are deleted after 30 days, offers a training opt-out in the dashboard and zero data retention for eligible enterprise customers. The policy does not say where SaaS data is processed. |
| Langfuse Cloud EU | Processor | cloud only, and only if keys are set | Traces of every step | Ireland (AWS `eu-west-1`), with backups copied to `eu-central-1` |
| Amazon Web Services | Processor (hosting) | hosted demo | Everything stored on the instance and its snapshots | Project Region, `eu-north-1` (Stockholm) by default in `infra/terraform/lean/variables.tf` |
| GitHub | Code, images, CI | build only | Source code, container images, evaluation reports with fictional data | Not used for production data |
| Let's Encrypt, sslip.io | Certificate authority; DNS for the demo hostname | hosted demo | Hostname only | Not personal data |

The **offline** profile sends no questions, answers or traces off the machine. It downloads models from Hugging Face on the first run.

The `production-reference` Terraform module (not deployed) grants access to Claude through Amazon Bedrock in the project Region, which would keep inference inside the company's AWS account. The application code has no Bedrock client yet (`src/gigawhat/models.py` uses the Anthropic API directly), so this option is not usable without a code change.

## 8. Data residency

- Postgres, the audit trail, approvals and checkpoints live on the EC2 instance in the project Region (default `eu-north-1`).
- On the cloud profile, masked questions and sources leave the UK and EU for Anthropic and Cohere. Anthropic's workspace data at rest is in the US; inference may run in any geography under the default setting. Cohere does not publish its SaaS location.
- Each such transfer needs a UK transfer mechanism, for example the International Data Transfer Agreement or Addendum, or the UK Extension to the EU-US Data Privacy Framework where the recipient is certified. Which applies to each processor has not been checked.

## 9. Security controls

| Control | Where |
|---|---|
| Row-level security on documents and records by business unit; nothing visible without a unit | Migration `0004_access_control.py` |
| Restricted reader role `gigawhat_reader` with SELECT only on documents and records; no access to `approvals`, `audit_events` or `feedback` | Migration `0004_access_control.py`; `create_reader_engine` in `src/gigawhat/db.py` |
| Append-only audit table | Migration `0005_oversight.py` |
| No SSH: no key pair, port 22 closed; administration through Session Manager | `infra/terraform/lean/compute.tf`, `network.tf` |
| IMDSv2 only, hop limit 1, so containers cannot reach the instance role's credentials | `infra/terraform/lean/compute.tf` |
| Secrets as SecureStrings in SSM Parameter Store, written to a root-only `.env` (mode 600) at deploy | `infra/README.md`; `fetch-env.sh` in `user_data.sh.tftpl` |
| Encrypted root volume and snapshots; seed bucket private, TLS-only, encrypted | `compute.tf`, `storage.tf` |
| Least-privilege instance and deploy roles; deploy through SSM with GitHub OIDC, no stored AWS keys | `iam.tf`, `infra/terraform/github-deploy/main.tf` |
| HTTPS with HSTS, nosniff and a strict referrer policy | `deploy/Caddyfile` |
| App container runs as a non-root user (uid 10001) | `Dockerfile` |
| File upload off; raw HTML in messages off | `.chainlit/config.toml` |

Weaknesses to fix before real use:

- The app logs in to Postgres as the database owner, which is the superuser created by the container's `POSTGRES_USER`. It can bypass the audit trigger. Use separate login roles: an owner for migrations only, a writer with INSERT only on `audit_events`, and the reader as its own login.
- Outside demo mode, `/api/audit` now returns 403 (`src/gigawhat/api.py`), but the Authorised Person queues show every pending request in a unit to anyone who chooses that persona. Demo mode must stay on until sign-on exists.
- `allow_origins = ["*"]` in `.chainlit/config.toml`.
- No WAF in front of the lean host (stated in `infra/README.md`).
- The AWS managed policy `AmazonSSMManagedInstanceCore` lets the instance read any parameter in the account (stated in `infra/README.md`).

## 10. Risks to individuals

| Risk | Likelihood (demo / production) | Severity | Main measures | Residual |
|---|---|---|---|---|
| Customer details sent to a processor abroad | Low / Medium | Medium | Masking before any model call; processors bound by terms | Medium until masking gaps close and transfer mechanisms are confirmed |
| Customer details kept indefinitely in an append-only log | Low / Medium | Medium | Masking before storage; entity types only | Medium until retention exists |
| Health or vulnerability details disclosed | Low / Medium | High | None specific | High for production |
| Staff decisions monitored unfairly (per-approver statistics) | n/a / Medium | Medium | Purpose limitation; transparency to staff | To be assessed with staff representatives |
| Questions and extracts seen by people who should not see them | Low (demo scoping) / High if demo mode is turned off without sign-on | High | Demo mode default; `/api/audit` refused outside demo mode | High until sign-on exists |

## 11. Questions a real DPO would still need to answer

1. Who is the controller, and is each provider a processor under a signed data processing agreement?
2. What is the lawful basis for processing customer details that staff type in, and for processing staff identity and decisions?
3. Is special category data (health, disability, vulnerability) likely, and if so what condition applies and what extra detection is needed?
4. Which transfer mechanism covers each processor outside the UK, and has a transfer risk assessment been done where needed?
5. Should `inference_geo` be set to `us`, or should Claude be reached through Bedrock in a UK or EU Region instead?
6. Should Cohere zero data retention, or a private Cohere deployment, be required?
7. What retention periods apply to audit events, approvals, checkpoints, feedback, traces, logs and snapshots, and who runs the purge?
8. How will erasure, access and rectification requests be met for data in an append-only audit trail?
9. Is Langfuse Cloud acceptable, or must traces be self-hosted? Should tracing be off by default in production?
10. Should staff be told, and should their representatives be consulted, before per-approver statistics are collected?
11. What privacy information will users and customers receive, and where?
12. Is the masking accuracy good enough? What test set of realistic, synthetic customer data will measure it, and what miss rate is acceptable?
13. Do real incident reports and work orders contain personal data that would be sent to the model as evidence, and should records be masked too?
14. Who may see the full audit trail, and how is that access logged?
15. What is the breach response if a processor or the host is compromised?
16. Should the DPIA be shared with or reviewed by the ICO under prior consultation, if high risk remains after mitigation?

## Sources

- ICO, Data protection impact assessments: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/guide-to-accountability-and-governance/data-protection-impact-assessments
- ICO, Guidance on AI and data protection (status note): https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/guidance-on-ai-and-data-protection/whats-new/
- Anthropic, Data residency: https://platform.claude.com/docs/en/manage-claude/data-residency
- Anthropic, API and data retention: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- Cohere, Enterprise data commitments: https://cohere.com/data-usage-policy
- Langfuse, Data regions: https://langfuse.com/security/data-regions
- EU AI Act, Article 26 (deployer log retention): https://artificialintelligenceact.eu/article/26/
