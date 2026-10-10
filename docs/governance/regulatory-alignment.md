# Regulatory alignment

| | |
|---|---|
| Status | Draft for the demo. Harrowmere Energy is fictional. |
| Written against | Commit `3e8cb02` plus the follow-up fixes made on 10 October 2026; regulatory sources checked on 10 October 2026 |
| Audience | Safety team, compliance, auditors, engineering |

**This is not legal advice.** It is an engineering view of how the design of a demo lines up with frameworks a UK utility would care about. A real deployment needs its own legal and regulatory review. Several of the documents cited are guidance or drafts and can change.

## 1. Summary

| Framework | Status | Applies to a GB-only utility? | Short answer for GigaWhat |
|---|---|---|---|
| EU AI Act (Regulation (EU) 2024/1689), as amended by the Digital Omnibus on AI (Regulation (EU) 2026/1744) | In force; Annex III high-risk obligations apply from 2 December 2027 | Only if established in the EU or if outputs are used in the EU (Article 2(1)) | Designed to stay advisory, so it is unlikely to be a "safety component" under Annex III point 2. It mirrors most high-risk obligations anyway. |
| UK AI regulation principles | Non-statutory, applied by existing regulators | Yes | Mapped below |
| Ofgem, "Ethical AI use in the energy sector (version 2)", 13 May 2026 | Good practice guidance | Yes, for GB energy licensees and other stakeholders | Mapped below |
| HSE: Health and Safety at Work etc. Act 1974 and HSE's stated approach to AI; HSG250, HSG253; competence duties | Law and guidance | Yes | GigaWhat quotes procedures; it does not replace the permit-to-work system or competence |
| ISO/IEC 42001:2023 | Voluntary, certifiable standard | Optional | GigaWhat supplies system-level evidence; the management system is the company's |
| NIST AI RMF 1.0 | Voluntary framework | Optional | Useful structure for the risk work |

## 2. EU AI Act

### Does it apply?

The Act applies to providers placing AI systems on the EU market, to deployers established or located in the EU, and to providers and deployers in third countries where the system's output is used in the EU (Article 2(1)(a) to (c)). A utility operating only in Great Britain, using GigaWhat only in Great Britain, would normally fall outside it. It is still useful as a benchmark, and a group with EU operations could be in scope.

### Is GigaWhat a "safety component" of critical infrastructure?

Annex III point 2 lists as high-risk: "AI systems intended to be used as safety components in the management and operation of critical digital infrastructure, road traffic, or in the supply of water, gas, heating or electricity."

Article 3(14) defines a safety component as "a component of a product or of an AI system which fulfils a safety function for that product or AI system, or the failure or malfunctioning of which endangers the health and safety of persons or property". Recital 55 narrows this for critical infrastructure: safety components "are systems used to directly protect the physical integrity of critical infrastructure or the health and safety of persons and property but which are not necessary in order for the system to function".

The European Commission published **draft** guidelines on high-risk classification under Article 6 on 19 May 2026 for stakeholder consultation. We found no final version at the time of writing. The draft says:

- the assessment "must focus on whether the AI system directly protects the physical integrity of the infrastructure by reducing, preventing, controlling, or mitigating risks" (paragraph 180);
- the safety-function requirement "excludes from high-risk classification AI systems which are merely supportive, informational, organisational or optimisation-oriented ... and which do not themselves perform such a direct protective function" (paragraph 181);
- an AI system should be a safety component only if it performs one of six listed safety functions, such as detecting dangerous situations, detecting a need for maintenance whose omission may directly lead to harm, preventing operations from starting, controlling or limiting harm, triggering a safe stop, or supervising another safety system (paragraph 184);
- the availability of a redundant system that directly protects the infrastructure should be considered (paragraph 186);
- the use case covers only entities identified as critical entities by a Member State under the Critical Entities Resilience Directive (paragraph 190);
- for gas, a predictive maintenance tool for pipeline monitoring falls outside the high-risk use case because it "does not directly control safety functions and existing safety systems remain independently operational".

On that reading, GigaWhat is informational. It retrieves and quotes approved procedures and summarises records when asked. It does not monitor plant, trigger actions or supervise a safety system, and the permit-to-work and isolation systems remain independent of it. It is therefore **unlikely** to be a safety component under Annex III point 2. Two cautions:

1. The guidelines are a draft and the Court of Justice has the final word.
2. Paragraph 184(b) covers systems that detect the need to schedule maintenance or inspections. GigaWhat summarises inspection trends on request; it does not monitor or schedule. A future feature that watched assets and raised maintenance needs would need a fresh assessment.

If a system does fall within Annex III, the Article 6(3) route out (for example a "narrow procedural task" or a "preparatory task") requires the provider to document its assessment and register the system (Article 6(4)).

### Why the design keeps it advisory

- No connection to plant, SCADA or OT; read-only tools only (`src/gigawhat/assistant/evidence.py`).
- No model writes steps for safety-critical work; code quotes the approved procedure (`src/gigawhat/assistant/responses.py`).
- An Authorised Person must release safety-critical extracts, and a release is not a permit ([human-oversight.md](human-oversight.md)).
- Emergencies get fixed text directing people to 999 and the emergency services, nothing else.
- Every outcome is logged, so the advisory role can be shown after the fact.

### Timeline

Regulation (EU) 2026/1744 (the Digital Omnibus on AI) was published in the Official Journal on 24 July 2026 and entered into force on 27 July 2026. It moved the application of obligations for Annex III high-risk systems from 2 August 2026 to 2 December 2027, and for Annex I systems to 2 August 2028.

### High-risk obligations GigaWhat mirrors anyway

| Article | Obligation | GigaWhat |
|---|---|---|
| 9 | Risk management system | [risk-register.md](risk-register.md) |
| 10 | Data and data governance | Document register with validation and immutable versions; fictional, documented dataset (`data/README.md`) |
| 11 | Technical documentation | `docs/architecture.html` and this pack |
| 12 | Record-keeping: automatic logging of events over the system's lifetime | `audit_events`, append-only (migration `0005_oversight.py`) |
| 13 | Transparency and information for deployers | [system-card.md](system-card.md) |
| 14 | Human oversight, including awareness of automation bias (14(4)(b)) and the ability to interrupt the system with a "stop" button or similar (14(4)(e)) | Approval flow; pause switch (`GIGAWHAT_PAUSED`) |
| 15 | Accuracy, robustness and cybersecurity | Release gates, red-team set, security controls |
| 26(2) | Deployers assign oversight to people with the necessary competence, training and authority | Authorised Persons; not checked by the system |
| 26(6) | Deployers keep logs for at least six months | No retention policy yet; see [data-protection.md](data-protection.md) |
| 50(1) | People are informed that they are interacting with an AI system | The demo banner says answers are written by AI, and every answer ends "Written by AI from approved documents; check the cited sources." (`src/gigawhat/ui/chat.py`, `AI_NOTE` in `responses.py`) |

## 3. UK approach to AI regulation

The government's white paper "A pro-innovation approach to AI regulation" (29 March 2023) set five cross-sector principles for existing regulators to apply. The government response of 6 February 2024 confirmed them on a non-statutory basis and asked a number of regulators, including Ofgem, to set out their approach.

| Principle | GigaWhat |
|---|---|
| Safety, security and robustness | Safety tiers with a rule floor; strict mode; release gates; red-team set; row-level security; no plant connection |
| Appropriate transparency and explainability | Citations on every claim; source text in a side panel; parts of the question the sources do not cover; an AI-written note on every answer; step list "How GigaWhat handled this"; system card |
| Fairness | Limited relevance: GigaWhat does not make decisions about customers or staff. Per-approver statistics, if adopted, must be used fairly. |
| Accountability and governance | Named roles for the rules file and register; audit trail with prompt version and models; change control. Named owners still needed. |
| Contestability and redress | Users can decline to act, press Not helpful, and escalate to their Authorised Person or document controller. No formal route to contest an output yet. |

## 4. Ofgem guidance

Ofgem published "Ethical AI use in the energy sector" in May 2025 and **version 2** on 13 May 2026. It is good practice guidance that complements, and does not replace, existing legal and regulatory obligations. It frames four outcomes (safe, secure, fair and environmentally sustainable AI) and sets good practices under Governance and policies (Practices 1 to 5), Risk (Practices 1 to 9) and Competencies (Practices 1 to 4). Version 2 added Governance Practice 5 on proportionate organisational transparency and explainability.

Practices most relevant to GigaWhat:

| Ofgem practice | GigaWhat |
|---|---|
| Governance Practice 2: effective accountability and governance across the life cycle | [change-control.md](change-control.md); owners not yet named |
| Governance Practice 5: records that explain the basis of AI decisions; ways for users to escalate outputs that appear wrong | Audit trail with sources and verification drops; abstain and decline texts point to the Authorised Person and document controller |
| Project governance: change control, testing, review, record keeping, educating users (paragraph 3.12) | CI, evaluation, change control; user training not yet defined |
| Risk Practice 2: evidence-led risk assessment, recorded | [risk-register.md](risk-register.md) |
| Risk Practice 5: identify failure modes; consider engineering protection or human intervention; watch for loss of skills | Hazard log; strict mode; approvals. Skill fade is not addressed. |
| Risk Practice 6: confidence in performance, with metrics | Release gates and quality targets ([evaluation-report.md](evaluation-report.md)) |
| Risk Practice 8: human oversight from the earliest stage; consider overconfidence and lack of trust | Approval flow; automation-bias measures in [human-oversight.md](human-oversight.md), section 12 |
| Risk Practice 9: monitor and review | Langfuse tracing (optional), feedback, audit; no regular review cadence yet |
| Competencies Practices 1 and 2: training plans; suitably qualified decision makers | Not covered by the system |
| Appendix 3: AI supply chain management | Pinned actions and lockfile; HSE downloads checked against registered checksums; code owners for rules, prompts, register and evaluation sets; images built only after CI passes; gaps in [risk-register.md](risk-register.md) H17 |

## 5. Health and safety (HSE)

**General duty.** HSE's stated approach is that the Health and Safety at Work etc. Act 1974 is goal-setting and so "applicable regardless of the technology being used", including AI. HSE expects a risk assessment for uses of AI that affect workplace health and safety, with controls that reduce risk so far as is reasonably practicable, including against cyber security threats.

**Permits and isolation.** HSG250, "Guidance on permit-to-work systems: a guide for the petroleum, chemical and allied industries" (2005), and HSG253, "The safe isolation of plant and equipment" (2006), describe the permit-to-work and isolation arrangements that control hazardous work. Both are in GigaWhat's corpus. GigaWhat sits outside these systems:

- it never issues, authorises or closes a permit, and a GigaWhat "release" is not a permit;
- it quotes the company's own approved procedure rather than generating steps, and tells the user to work to the full procedure and their permit;
- it treats permits, isolation, switching, purging and confined-space entry as safety-critical topics (`safety_topics.yaml`).

**Competence.** The Electricity at Work Regulations 1989, regulation 16, require that no one does work needing technical knowledge or experience to prevent danger unless they have it or are suitably supervised. The Management of Health and Safety at Work Regulations 1999, regulation 13, require employers to take capabilities into account when giving people tasks. For gas conveyors, the Gas Safety (Management) Regulations 1996 require a safety case and set duties for gas escapes (regulation 7). GigaWhat does not assess competence. It assumes the people holding the Authorised Person role are competent, which the company must assure. In the demo, anyone can choose that persona.

**Emergencies.** The emergency card points to 999, the gas emergency number 0800 111 999 and 105. GigaWhat is not part of the company's emergency arrangements.

## 6. ISO/IEC 42001 and the NIST AI RMF

**ISO/IEC 42001:2023** specifies requirements for establishing, implementing, maintaining and continually improving an AI management system in an organisation. It is about the organisation, not one system. GigaWhat can supply evidence to such a system: risk assessment (risk register), impact assessment (data protection), life-cycle and change records (change control), monitoring and evaluation (evaluation report), and human oversight. The policies, objectives, roles, internal audit and management review are the company's to provide.

**NIST AI Risk Management Framework 1.0** (26 January 2023) is voluntary and organises AI risk work into four functions: Govern, Map, Measure and Manage. NIST published a Generative AI Profile (NIST AI 600-1) on 26 July 2024 and, on 7 April 2026, a concept note for an AI RMF profile on trustworthy AI in critical infrastructure. NIST says the AI RMF is being revised.

| NIST function | GigaWhat evidence |
|---|---|
| Govern | Change control, named file owners for rules and register, audit trail |
| Map | System card (purpose, users, out-of-scope uses, context) |
| Measure | Golden and red-team sets, release gates, DeepEval scores |
| Manage | Risk register controls, pause switch, approvals |

## 7. Mapping table

| Requirement or principle | How GigaWhat addresses it | Evidence (file or test) | Gap for a real deployment |
|---|---|---|---|
| EU AI Act Annex III point 2: avoid being a safety component | Advisory only; no plant connection; quotes procedures; humans release | `src/gigawhat/assistant/evidence.py`; `graph.py`; `tests/test_graph.py::test_safety_critical_answer_never_asks_the_model_to_write` | Record a formal classification assessment; revisit when the final Commission guidelines are adopted or any monitoring feature is added |
| EU AI Act Art. 9, risk management | Hazard log with controls and verification | [risk-register.md](risk-register.md) | Named owner, review cadence, sign-off |
| EU AI Act Art. 10, data governance | Register is the source of truth; validated; immutable versions | `src/gigawhat/corpus/register.py`; `ingest.py`; `src/gigawhat/corpus/hse.py`; `tests/test_ingest.py::test_editing_a_published_version_is_refused`; `tests/test_hse.py::test_refuses_a_download_that_does_not_match_the_registered_checksum` | Real document-control integration |
| EU AI Act Art. 12 and 26(6), logging and retention | Append-only audit events with prompt version and models | Migration `0005_oversight.py`; `tests/test_graph.py::test_release_and_request_are_both_audited` | Retention policy; separate writer role; off-host copy; app version in each event |
| EU AI Act Art. 13 and 50(1), transparency | System card; citations; banner and closing note saying answers are written by AI | [system-card.md](system-card.md); `src/gigawhat/ui/chat.py`; `responses.py` (`AI_NOTE`) | No automated test of the AI note |
| EU AI Act Art. 14, human oversight | Approval through `interrupt()`, with the extract withheld until release; separation of duties in code and database; expiry; full extract and a required note for the decider; pause switch that also blocks decisions | `oversight.py`; migration `0005_oversight.py`; `tests/test_graph.py::test_requester_does_not_see_the_extract_before_release`, `::test_requester_cannot_release_their_own_request`, `::test_expired_request_cannot_be_released`, `::test_paused_assistant_refuses_decisions` | Identity-based separation of duties; evidence that the extract was read; pause without restart |
| EU AI Act Art. 15, accuracy and robustness | Release gates; quote checks; abstention | `src/gigawhat/evaluation/report.py`; `answer.py`; `tests/test_answer.py` | Evaluation in the release pipeline; larger, realistic test sets |
| EU AI Act Art. 15, cybersecurity | Input guardrail; row-level security; no SSH; IMDSv2; secrets in Parameter Store | `rails.py`; migration `0004_access_control.py`; `infra/terraform/lean` | Least-privilege database logins; WAF; image digests; penetration test |
| EU AI Act Art. 26(2), competent overseers | Authorised Person persona | `src/gigawhat/personas.py` | Sign-on with group membership tied to real appointments |
| UK principle: safety, security, robustness | Tiers, strict mode, gates, red-team | `safety_topics.yaml`; `evals/redteam.yaml` | As above |
| UK principle: transparency and explainability | Citations, gaps, AI note, step list, system card | `responses.py`; `service.py` (`STEP_LABELS`) | Verify claim wording against quotes |
| UK principle: accountability and governance | Audit trail; change control; code owners | `audit_events`; [change-control.md](change-control.md); `.github/CODEOWNERS` | Named owners; branch protection that requires code-owner review |
| UK principle: contestability and redress | Users can ignore output, press Not helpful, escalate | `feedback` table; abstain and decline texts | A formal route to challenge an output, with responses tracked |
| Ofgem Governance Practice 5: records explaining outputs; escalation | Audit events hold sources, tier reasons and verification drops | `graph.py` (`_event`) | Escalation workflow; feedback reasons |
| Ofgem Risk Practice 5: failure modes and human intervention | Hazard log; approvals; pause; failures audited and reported as a fixed service-error message | [risk-register.md](risk-register.md); `tests/test_graph.py::test_failed_model_call_is_audited` | Skill-fade monitoring |
| Ofgem Risk Practice 8: human and AI interaction | Approval flow; automation-bias measures | [human-oversight.md](human-oversight.md) | Sampling reviews; per-approver statistics |
| Ofgem Competencies | Not addressed by the system | None | Training plan for users and Authorised Persons |
| HSWA 1974 and HSE's AI approach: risk assessment | Hazard log | [risk-register.md](risk-register.md) | Integrate with the company's safety management system |
| HSG250 permit-to-work | GigaWhat never issues permits; quotes procedures | `responses.py` (`STRICT_PREFACE`); `INPUT_POLICY` in `prompts.py`; red-team R005 to R007 | Check the permit number given in the release note against the permit system |
| HSG253 safe isolation | Isolation is safety-critical; extracts only; Authorised Person release | `safety_topics.yaml` (`isolation-earthing`); `tests/test_tiers.py::test_wanting_to_do_hazardous_work_is_safety_critical` | Wider phrasing coverage; conflict detection in strict mode |
| EAWR 1989 reg. 16 and MHSWR 1999 reg. 13: competence | Out of scope of the system | None | Competence checked through role assignment |
| ISO/IEC 42001 | System-level evidence in this pack | This pack | The organisation's AI management system |
| NIST AI RMF | Govern, Map, Measure, Manage evidence | Section 6 above | Adopt the critical infrastructure profile when published |

## Sources

EU AI Act and Digital Omnibus

- Regulation (EU) 2024/1689 (AI Act), EUR-Lex: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Regulation (EU) 2026/1744 (Digital Omnibus on AI), EUR-Lex: https://eur-lex.europa.eu/eli/reg/2026/1744/oj
- Cuatrecasas, "Digital Omnibus on AI has been published" (dates and application deadlines): https://www.cuatrecasas.com/en/spain/intellectual-property/art/digital-omnibus-ai-has-been-published
- AI Act Annex III: https://artificialintelligenceact.eu/annex/3/
- AI Act Article 2: https://artificialintelligenceact.eu/article/2/
- AI Act Article 3: https://artificialintelligenceact.eu/article/3/
- AI Act Article 6: https://artificialintelligenceact.eu/article/6/
- AI Act Article 12: https://artificialintelligenceact.eu/article/12/
- AI Act Article 14: https://artificialintelligenceact.eu/article/14/
- AI Act Article 26: https://artificialintelligenceact.eu/article/26/
- AI Act Article 50: https://artificialintelligenceact.eu/article/50/
- AI Act Recital 55: https://artificialintelligenceact.eu/recital/55/
- European Commission, Draft guidelines on the classification of high-risk AI systems (19 May 2026): https://digital-strategy.ec.europa.eu/en/library/draft-commission-guidelines-classification-high-risk-ai-systems
- Draft guidelines, Annex III document (copy used for paragraph references): https://www.dirittobancario.it/wp-content/uploads/2026/05/Draft-Guidelines-on-the-classification-of-high-risk-AI-Annex-III.pdf

UK

- DSIT, "A pro-innovation approach to AI regulation" (white paper, 29 March 2023): https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach/white-paper
- Government response (6 February 2024): https://www.gov.uk/government/consultations/ai-regulation-a-pro-innovation-approach-policy-proposals/outcome/a-pro-innovation-approach-to-ai-regulation-government-response
- Ofgem, "Ethical AI use in the energy sector": https://www.ofgem.gov.uk/guidance/ethical-ai-use-energy-sector
- Ofgem, version 2 PDF (13 May 2026): https://www.ofgem.gov.uk/sites/default/files/2026-05/ethical-ai-use-in-the-energy-sector.pdf
- HSE, "HSE's regulatory approach to Artificial Intelligence (AI)": https://www.hse.gov.uk/news/hse-ai.htm
- HSE, HSG250: https://www.hse.gov.uk/pubns/books/hsg250.htm
- HSE, HSG253: https://www.hse.gov.uk/pubns/books/hsg253.htm
- Electricity at Work Regulations 1989, regulation 16: https://www.legislation.gov.uk/uksi/1989/635/regulation/16
- Management of Health and Safety at Work Regulations 1999, regulation 13: https://www.legislation.gov.uk/uksi/1999/3242/regulation/13
- Gas Safety (Management) Regulations 1996: https://www.legislation.gov.uk/uksi/1996/551/contents

Standards and frameworks

- ISO/IEC 42001:2023: https://www.iso.org/standard/42001 (summary also at https://webstore.iec.ch/publication/90574)
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST, Concept note for an AI RMF profile on trustworthy AI in critical infrastructure: https://www.nist.gov/programs-projects/concept-note-ai-rmf-profile-trustworthy-ai-critical-infrastructure
