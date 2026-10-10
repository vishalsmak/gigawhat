# Human oversight

| | |
|---|---|
| Status | Draft for the demo. Harrowmere Energy is fictional. |
| Written against | Commit `3e8cb02` plus the follow-up fixes made on 10 October 2026 |
| Audience | Safety team, Authorised Persons, auditors, engineering |

GigaWhat is advisory. This document explains how people stay in control: which questions need a human decision, how that decision is made and recorded, how the service is stopped, and where the current build falls short of what a real deployment would need.

## 1. What the assistant cannot do

The strongest oversight control is what the system is unable to do.

- It has no connection to plant, SCADA or OT. Its only tools are six read-only queries over copies of records in its own database (`src/gigawhat/assistant/evidence.py`).
- No model can release or decline a request. Only an Authorised Person persona's action in the chat interface calls `Oversight.decide` (`src/gigawhat/assistant/oversight.py`).
- For safety-critical questions no model writes any text. Code copies the procedure (`src/gigawhat/assistant/responses.py`).
- It cannot see documents or records outside the persona's business units. Row-level security in the database enforces this (migration `0004_access_control.py`).

## 2. The four safety tiers

| Tier | Example (gas) | Example (electricity) | What GigaWhat does | Human role |
|---|---|---|---|---|
| Routine | Who owns the meter-reading schedule procedure? | Where is the substation access procedure? | Cited answer, checked in code, ending with a note that it was written by AI | Reader judges the answer |
| Safety-relevant | When was governor G-112 last inspected, and what was found? | Summarise this month's oil-temperature alarms on T-104 | As routine, plus the banner "Safety-relevant: check the cited procedure before acting on this." | Reader checks the cited procedure before acting |
| Safety-critical | How do I purge the 75 mbar main on Mill Lane? | Steps to isolate and earth the 11 kV feeder at Ashford Road? | Strict mode: word-for-word extracts, no model-written text, held back until an Authorised Person releases them | Authorised Person releases or declines; work is still done under the permit system |
| Emergency | Strong smell of gas outside number 14 | Someone has had a shock at the substation | Fixed emergency card only: 999, 0800 111 999, 105 | The person acts at once; GigaWhat does nothing else |

Examples are taken from `docs/architecture.html`.

### How the tier is chosen

1. Fixed rules in `src/gigawhat/assistant/safety_topics.yaml` run first. The file is owned by the Electricity Safety Manager and the Gas Safety Manager (its header says so), changes to it need code-owner review (`.github/CODEOWNERS`), and it must pass the safety evaluation set before release. A safety-critical match needs both an intention to act ("how do I", "steps to", "can I", "how high", "minimum") and a hazardous topic (isolation, switching, permits, purging, confined space, pressure work, live working, excavation).
2. If a rule finds an emergency, the emergency card is shown at once. No model is asked (`tests/test_graph.py::test_emergency_is_answered_without_asking_any_model`).
3. Otherwise the input guardrail and a model classifier run in parallel. The classifier's prompt tells it to choose the more serious tier when unsure (`TIER_PROMPT` in `prompts.py`).
4. The stricter of the rule result and the classifier result is used (`stricter` in `tiers.py`). The classifier can raise the tier but never lower it below the rules (`tests/test_graph.py::test_rules_escalate_when_the_model_underrates_the_question`).
5. An emergency found by the classifier beats a blocked input (`tests/test_graph.py::test_model_spotted_emergency_beats_a_block`).

## 3. Strict mode

For a safety-critical question, after retrieval (`prepare_release` in `src/gigawhat/assistant/graph.py`):

- Code takes up to two sections of approved procedures (`STRICT_EXTRACTS = 2`) that score at least 0.3 with the reranker (`STRICT_MIN_RELEVANCE`), a higher bar than the 0.2 an ordinary answer needs, so the loosest matches never reach an Authorised Person. A near miss can still get through (in the evaluation, G059 sent a section of a procedure that excludes the work asked about); the Authorised Person reads the extract and declines it. HSE guidance alone is never enough. Sections titled revision history, references, records, definitions, purpose, scope or responsibilities are skipped (`strict_extracts`).
- If nothing qualifies, GigaWhat abstains and no request is raised (`tests/test_graph.py::test_guidance_alone_is_not_released_for_safety_critical_work`, `::test_weakly_matching_procedure_is_not_sent_for_release`; `tests/test_responses.py`).
- The extract is built by `render_extracts`: the quoted sections under a fixed preface ("Safety-critical work: an Authorised Person must release this before you act. The extracts below are copied word for word from the approved procedure. GigaWhat has not written, reordered or changed any step. Work to the full procedure and your permit, not to these extracts alone."), with a notice for any document past its review date. It is kept in graph state and in the approval request, not shown to the requester.
- **The requester sees only which sections are waiting** (`pending_notice`): "Waiting for an Authorised Person (APR-...). This is safety-critical work, so GigaWhat has sent these sections of the approved procedure for release:", a list of section labels and titles, then "They will be shown here word for word once an Authorised Person releases them. Do not start the work until then." Overdue notices are shown too. The source panel carries labels with no text.

Tests: `tests/test_graph.py::test_extract_for_the_authorised_person_is_the_procedure_word_for_word`, `::test_requester_does_not_see_the_extract_before_release`, `::test_requester_is_told_which_sections_await_release`, `::test_safety_critical_answer_never_asks_the_model_to_write`.

## 4. The approval flow

| Step | What happens | Where |
|---|---|---|
| 1 | Strict-mode extract is prepared | `prepare_release` and `render_extracts` |
| 2 | A row is added to `approvals` with status `pending`, an ID such as `APR-3F9A1C`, the requester's browser ID and persona, the business unit that will decide it, the masked question, the citations and the extract text | `Oversight.request_approval` |
| 3 | The deciding unit is the one that owns the procedure. A company-wide (`shared`) procedure goes to the requester's own unit | `_release_unit` in `graph.py` |
| 4 | Audit event `approval_requested` is written | `graph.py` |
| 5 | The graph calls LangGraph's `interrupt()` and stops. Its state, including the extract, is saved by the Postgres checkpointer, so the wait survives restarts | `await_decision` in `graph.py`; `open_checkpointer` in `service.py` |
| 6 | The requester sees the pending notice (section labels only) | `pending_notice` in `responses.py`; `_send_turn` in `src/gigawhat/ui/chat.py` |
| 7 | An Authorised Person for that unit opens the persona and sees the request in their queue. Requests older than 24 hours are left out | `pending_for` and `APPROVAL_TTL` in `oversight.py`; `_show_queue` in `chat.py` |
| 8 | They read the full extract in the side panel and press Release or Decline, then type a note | `on_release`, `on_decline`, `_ask_for_note` in `chat.py` |
| 9 | The decision is refused if GigaWhat is paused. The note is masked for personal data | `Assistant.decide` in `service.py` |
| 10 | The rules are checked (section 5) and the row is updated with the decision, time, decider and note. If the update does not change exactly one pending row, the decision is refused | `Oversight.decide`, `_check_may_decide` |
| 11 | The graph resumes with `Command(resume=...)` carrying the decision, the decider's persona, the decider's browser ID and the masked note | `Assistant.decide` |
| 12 | The response becomes "Released by ..." with the note and the full extract, or "Declined by ..." with the note and no extract or sources | `released`, `declined` in `responses.py`; `apply_decision` in `graph.py` |
| 13 | Audit event `released` or `declined` is written | `audit` in `graph.py` |
| 14 | The requester sees the outcome under "Your requests" or with "Check status" | `_show_my_requests`, `on_show_outcome` in `chat.py` |

Tests: `tests/test_graph.py::test_request_goes_to_the_unit_that_owns_the_procedure`, `::test_company_wide_procedure_goes_to_the_requesters_unit`, `::test_pending_request_appears_in_the_authorised_persons_queue`, `::test_authorised_person_releases_the_extract`, `::test_released_answer_contains_the_extract`, `::test_release_and_request_are_both_audited` (events are exactly `approval_requested` then `released`).

## 5. Separation of duties

| Rule | In code (`_check_may_decide` and `Oversight.decide` in `oversight.py`) | In the database (migration `0005_oversight.py`) |
|---|---|---|
| The requester cannot release their own request | Rejects a decider whose persona equals the requester's | CHECK `decider_is_not_requester`: `decider_persona IS NULL OR decider_persona <> requester_persona` |
| Only an Authorised Person for the request's unit can decide | Rejects a persona whose `releases_for` is not the request's business unit | None |
| A request is decided once | Rejects a request that is not `pending`; the update requires `status = 'pending'` and must change exactly one row, so of two simultaneous decisions only one succeeds | CHECK `valid_status` (`pending`, `released`, `declined`) and CHECK `decision_has_timestamp` |
| A request cannot be decided after it expires | Rejects a request raised more than 24 hours ago (`APPROVAL_TTL`) | None |

Tests: `tests/test_graph.py::test_requester_cannot_release_their_own_request`, `::test_other_business_unit_cannot_release`, `::test_decided_request_cannot_be_decided_again`, `::test_only_one_of_two_simultaneous_decisions_succeeds`, `::test_expired_request_cannot_be_released`. No test writes to the table directly to prove the database constraint on its own.

Limits of the current design:

- **Both checks compare personas, not people.** In the demo one visitor raises a request as a field engineer, switches to the Authorised Person persona and releases it. That is intended for the demo and is not separation of duties. A real deployment must compare authenticated identities as well (for example `decider_user <> requester_user`) in code and in the CHECK constraint.
- A request made by an Authorised Person persona can only be released by a different persona of the same unit. In the demo there is only one Authorised Person persona per unit, so such a request cannot be released. It expires after 24 hours.
- For the document controller and auditor, whose units include both gas and electricity, a company-wide procedure goes to the gas Authorised Person, because gas is the first unit in their profile.

## 6. The decline path

1. The Authorised Person presses Decline.
2. GigaWhat asks: "Why are you declining? This goes to the requester." (`_ask_for_note` in `chat.py`).
3. A note is required. If the reply is empty, or none arrives within 10 minutes, GigaWhat says "Nothing was decided: a note is needed." and the request stays pending.
4. The note is masked for personal data (`tests/test_graph.py::test_decision_note_is_masked_before_it_is_stored`) and stored in `approvals.decision_note`, in graph state and in the audit event.
5. The requester sees "**Declined by Authorised Person (Gas).** <note> Do not start this work. Speak to your Authorised Person before going any further." The response carries no extract and no sources (`tests/test_graph.py::test_declined_answer_carries_no_sources`).

Release works the same way: GigaWhat asks "What did you check before releasing? For example the permit number and site conditions. This is recorded in the audit trail." and nothing is released without a note.

## 7. What an Authorised Person sees

Each queued request is shown as a card (`_approval_card` and `_show_queue` in `chat.py`) with:

- the approval ID, the requester's persona title and the time it was raised;
- the masked question;
- the citations, for example `PR-GAS-031 v3 §6.2`, and the instruction "Read the full extract in APR-... before deciding.";
- the first 600 characters of the extract as a preview;
- the full extract as a side panel named after the approval ID;
- Release and Decline buttons, each followed by the request for a note.

The card does not show the tier reasons or the requester's identity beyond the persona. Nothing records whether the side panel was opened.

In demo mode the queue shows only requests raised from the same browser, so visitors do not see each other's questions. Outside demo mode it shows every unexpired pending request for the unit.

## 8. The record of the decision

| Where | What is recorded |
|---|---|
| `approvals` row | Status, `decided_at`, `decider_visitor` (browser ID), `decider_persona`, `decision_note` (masked) |
| `audit_events`, event `released` or `declined` | `guardrails.decision` holds `decision`, `decider_persona`, `decider_visitor` and the masked `note`. The event also holds the tier, sources, the response text, the prompt version and the model names. |

`tests/test_graph.py::test_release_event_names_the_decider` proves the audit event names the deciding persona, and `::test_release_through_the_service_records_who_released` proves that a release made through `Assistant.decide` records the decider's browser ID.

The audit event's own `visitor_id` and `persona` columns are still the **requester's**. An auditor must read the decider from `guardrails.decision`. A real deployment should record the decider's authenticated identity.

## 9. Demo mode and production

`GIGAWHAT_DEMO_MODE` (default `true`) is the only switch in the code (`src/gigawhat/config.py`).

| | Demo (built) | Production (intended, not built) |
|---|---|---|
| Identity | Random browser ID in the `gw_visitor` cookie (`src/gigawhat/ui/visitor.py`, `api.py`) | Single sign-on, for example Amazon Cognito |
| Role | Visitor picks a persona from Chainlit chat profiles | Persona derived from the user's groups, for example Cognito groups |
| Authorised Person queue | Only requests from the same browser | All unexpired pending requests for the unit (already the behaviour when demo mode is off) |
| Auditor view | This browser's events | Everyone's events, to authorised auditors only |
| `/api/audit` | This browser's events; nothing without the cookie | Returns 403 when demo mode is off, because the full trail needs sign-on (`src/gigawhat/api.py`; `tests/test_api.py`) |

`docs/architecture.html` now states that single sign-on is not built and that separation of duties compares personas. Until it is built, demo mode must stay on: with it off, anyone can choose the Authorised Person persona and see and decide every pending request in a unit.

## 10. Users' own oversight

- Every answer cites its sources, and the source text opens in a side panel.
- Parts of the question the sources do not answer are listed under "Not covered by the sources".
- Every answer ends "Written by AI from approved documents; check the cited sources.", and the demo banner says answers are written by AI.
- The step "How GigaWhat handled this" lists which stages ran (`STEP_LABELS` in `service.py`), so a user can see that a safety gate or quote check happened.
- Notices flag overdue documents. Safety-relevant answers carry a banner.
- If a model or service fails, the user is told that nothing was decided and to use their procedures and Authorised Person (`service_error` in `responses.py`).
- Answers have Helpful and Not helpful buttons, recorded in `feedback`.

## 11. The pause switch

`GIGAWHAT_PAUSED` (setting `paused` in `config.py`, default `false`) is the operations team's stop switch.

When it is `true`:

- `Assistant.ask` returns a fixed message straight away: "GigaWhat is paused by the operations team and is not answering questions at the moment. Use your procedures and your Authorised Person as normal." Nothing is masked, retrieved or sent to any model (`tests/test_graph.py::test_paused_assistant_answers_nothing`).
- `Assistant.decide` refuses every release and decline (`tests/test_graph.py::test_paused_assistant_refuses_decisions`).
- `/health` reports `"status": "paused"`.

Still open:

- The switch is read when the process starts. Changing it needs a restart of the app container. `/health` shows the state the running process is actually in, so use it to confirm.
- Paused replies are not written to the audit trail.

On the lean AWS host: set the parameter, then recreate the app container so it reads the new value.

```sh
aws ssm put-parameter --name /gigawhat/GIGAWHAT_PAUSED --type String --value true --overwrite
# then, in a Session Manager shell on the instance:
sudo /opt/gigawhat/fetch-env.sh
sudo docker compose -f /opt/gigawhat/docker-compose.prod.yml up -d --force-recreate app
```

Confirm that `/health` reports `paused`. Reverse with `--value false` and the same two commands.

Recommended for production: read the switch without a restart and audit each paused reply and each change of state.

## 12. Rubber-stamping and automation bias

An approval step only helps if the Authorised Person actually checks. The current build supports that:

- the requester cannot see the extract until it is released, so the release is what makes the text available;
- the full extract is attached to the request, and the card says to read it before deciding;
- extracts are copied word for word, so there is nothing paraphrased to second-guess;
- each extract carries its document, version and section, and overdue documents carry a notice;
- the preface says to work to the full procedure and the permit;
- release and decline both need a note in the decider's own words, and the release prompt asks for the permit number and site conditions;
- requests expire after 24 hours;
- every decision is attributed and audited.

What it does not do:

- nothing checks that the full extract was opened before Release;
- the note is free text: nothing checks that it names a real permit;
- nothing measures how carefully decisions are made.

Recommended for production:

1. Enable Release only after the Authorised Person has opened the full extract and the source documents.
2. Ask for the permit number in its own field and check it against the permit system.
3. Set the expiry period with the safety team (for example one shift).
4. **Sampling reviews of releases.** Each month a senior Authorised Person reviews a random sample of releases against the permit records and the full procedure, and logs the result.
5. **Per-approver statistics.** Report each approver's release rate, decline rate, median time from request to decision, and decisions per hour. Investigate very fast decisions and approvers who never decline. Agree this with staff representatives first ([data-protection.md](data-protection.md), section 11).
6. Train Authorised Persons on what GigaWhat does and does not check (the [system card](system-card.md), section 7) and on automation bias.
7. Feed the results into the [risk register](risk-register.md) (H09) and the release decision for each new version.
