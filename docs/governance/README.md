# GigaWhat governance pack

This folder holds the governance documents for GigaWhat, an AI assistant that helps operational staff at a gas and electricity utility find approved procedures, see the evidence behind them and get suggested next steps, with people making every decision.

**It describes a demo.** GigaWhat is a reference implementation built to production standards and run with fictional data. Harrowmere Energy, its sites, staff, customers, procedures and records are invented. The public HSE guidance in the corpus is real and is downloaded, not redistributed. The pack is written as if the demo were heading for real use, so that it shows what such a pack contains and where the current build would fall short.

Every statement is meant to be checkable against the repository. Each document names the files, tests and evaluation gates it relies on, and says plainly where something is missing. All were written against commit `3e8cb02` and updated for the follow-up fixes made on 10 October 2026.

## The documents

| Document | What it covers | Main readers |
|---|---|---|
| [system-card.md](system-card.md) | Purpose, users, out-of-scope uses, the two profiles and their models, data sources, how answers are produced, known limitations, how to report a problem | Everyone; start here |
| [risk-register.md](risk-register.md) | Hazard log: 21 hazards with cause, consequence, controls, verification and residual risk | Safety team, auditors, engineering |
| [human-oversight.md](human-oversight.md) | Safety tiers, strict mode, the approval flow, separation of duties, the decline path, what an Authorised Person sees, demo versus production, the pause switch, automation bias | Safety team, Authorised Persons, auditors |
| [data-protection.md](data-protection.md) | DPIA-style assessment: data flows, personal data, masking, storage and retention, processors, residency, security controls, open questions | Data protection officer, security |
| [change-control.md](change-control.md) | What is versioned, how a change ships, release gates, CI and evaluation workflows, rollback | Engineering, safety team, document controller, auditors |
| [regulatory-alignment.md](regulatory-alignment.md) | EU AI Act, UK AI principles, Ofgem guidance, HSE expectations, ISO/IEC 42001, NIST AI RMF, with a mapping table and sources. Not legal advice. | Compliance, safety team, auditors |
| [evaluation-report.md](evaluation-report.md) | Evaluation method, case sets, gates and targets, how to run it, and the latest results | Safety team, engineering, auditors |

### Suggested reading by role

- **Safety team:** system card, risk register, human oversight, then the evaluation report. The safety-tier rules in `src/gigawhat/assistant/safety_topics.yaml` are yours to own.
- **Data protection officer:** data protection, then the system card. Section 11 of the data protection document lists the questions that still need your answer.
- **Auditors:** risk register (every control has a named test or gate), change control (what the audit trail records and what it does not), human oversight sections 5 and 8.
- **Engineering:** the gaps in every document. Most have a concrete fix.

## Main open gaps

These matter most before any real use. Each is explained in the document named.

1. **No authentication.** Personas are chosen, not signed in to, and separation of duties compares personas rather than people. `/api/audit` now refuses requests outside demo mode, but turning demo mode off without sign-on would still open every unit's approval queue to anyone ([human-oversight.md](human-oversight.md) sections 5 and 9; risks H10 and H18).
2. **The audit trail can be bypassed by the app's own database login**, which is the database superuser, and there is no retention process ([data-protection.md](data-protection.md) sections 6 and 9; risk H15).
3. **Model-written answers are only partly checked.** Quotes are verified; claim wording, next steps and the summary's wording are not ([system-card.md](system-card.md) section 7; risks H02 and H13).
4. **Approvals still rely on the Authorised Person's diligence.** A note and the full extract are now required and available, but nothing checks the extract was read, and there are no sampling reviews or per-approver statistics yet ([human-oversight.md](human-oversight.md) section 12; risk H09).
5. **Release and supply chain.** The evaluation is not a condition of deployment; rollback across a migration does not work with `deploy.sh`; the instance pulls deploy scripts from `main`; base images are pinned by tag and Hugging Face models by name only ([change-control.md](change-control.md); risk H17).
6. **Masking gaps**: names that match company place names, meter point numbers and health details are not detected ([data-protection.md](data-protection.md) section 5; risk H05).
7. **Evaluation blind spots**: only the offline profile has been evaluated, so the cloud profile's thresholds are uncalibrated. The judge is the same model that writes answers, and the sets are small and written by the builders ([evaluation-report.md](evaluation-report.md) section 9 and Latest results).
8. **Quality below target**: the third offline run passed every release gate, but citations (66%), red-team refusals (86%) and notices (44%) are below their targets. Each miss is analysed in [evaluation-report.md](evaluation-report.md) (Latest results).

## What a real deployment would need beyond this pack

- **Named owners** for the system, the risk register, the safety-tier rules, the document register, the evaluation sets and the DPIA, recorded in each document's header.
- **Sign-off** of each document and of each release by those owners, with the evidence (evaluation report, risk register review) attached to the release record.
- **A real DPIA**: reviewed by the data protection officer, with consultation of staff representatives and, if high risk remains after mitigation, prior consultation with the ICO. The document here is an engineering draft with no consultation behind it.
- **Legal review** of the regulatory position, especially if the company has operations in the EU.
- **Integration with the company's safety management system**: incident reporting, management of change, competence records for Authorised Persons and links to the permit-to-work system.
- **A review cadence**: the risk register and evaluation re-run at every release and at least quarterly; this pack reviewed at least yearly.

## Keeping the pack current

When code changes, the document that cites it should change in the same pull request. [change-control.md](change-control.md) section 3 lists which changes need an evaluation run and whose sign-off. The "Latest results" section of [evaluation-report.md](evaluation-report.md) is filled in from the most recent evaluation run.
