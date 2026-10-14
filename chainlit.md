# How to use GigaWhat

GigaWhat helps staff at **Harrowmere Energy**, a fictional UK gas and electricity network operator, find the approved procedure for a job, see the evidence behind it in operational records, and get suggested next steps. **People make the decisions.** GigaWhat never decides anything safety-critical and has no connection to plant or control systems.

## 1. Pick a persona

Use the menu at the top left. What you can see and do depends on the role.

| Persona | Unit | What they do here |
|---|---|---|
| 🟠 Gas field engineer | Gas | Ask about gas procedures, governors, mains and their records |
| 🔵 Electricity control room | Electricity | Ask about the 132/33/11 kV network, assets and alarms |
| 🟠 Authorised Person (Gas) | Gas | Release or decline colleagues' safety-critical gas requests |
| 🔵 Authorised Person (HV) | Electricity | Release or decline colleagues' safety-critical electricity requests |
| 🟣 Document controller | All, including drafts | See the document register and every version's status |
| 🟣 Auditor | All | See the audit trail of questions, sources and answers |

Each persona only sees its own unit's documents and records, plus company-wide ones. That is enforced by the database, not by the AI.

## 2. Ask a question

Click an example under the question box, or type your own. Every reply starts with a status:

| Status | What it means |
|---|---|
| ✅ **Answer** | Written from approved documents and records. Every claim cites its source, and every quote was checked against it. Click a citation to read the source. |
| ⏳ **Waiting for an Authorised Person** | Safety-critical work. You'll get the procedure's own words, not an AI summary, once an Authorised Person releases them. |
| 🟢 **Released** / 🔴 **Declined** | An Authorised Person has decided, with a note saying why. |
| 🚨 **Emergency** | Emergency numbers and immediate actions, shown at once without asking any AI model. |
| 🔍 **No approved procedure found** | GigaWhat won't guess. Ask your Authorised Person or the document controller. |
| ⛔ **Not something GigaWhat can help with** | For example, attempts to change its instructions or get round a permit. |

Boxes under a reply flag what to **check before relying on it**, such as a procedure overdue for review or one revised recently.

## 3. Try the approval flow

1. As a **Gas field engineer**, ask: _How high must the vent stack be when purging a PE main?_
2. Switch to **Authorised Person (Gas)**. Read the extract in the side panel, then **Release** or **Decline** it with a note.
3. Switch back to **Gas field engineer** and open the request under **Your requests**.

## Good to know

- Personal data you type (names, addresses, phone numbers) is masked before anything is stored or sent to a model.
- Every question, its sources and the outcome go to an append-only audit trail. The **Auditor** persona shows yours.
- Answers marked safety-relevant still need you to check the cited procedure before acting.

_This is a demo with invented data. Do not use it for real operational work._
