# GigaWhat

An AI assistant that helps operational staff at a gas and electricity utility find the approved procedure for a job, see the evidence behind it, and get suggested next steps. People make the decisions: GigaWhat never decides anything safety-critical, and it has no connection to plant or OT systems.

This is a reference implementation built to production standards and run as a demo. The utility, its procedures and its records are fictional. Public HSE guidance is downloaded by a script, not redistributed.

It is being restructured to the plan in [`docs/phase-1-architecture.md`](docs/phase-1-architecture.md): components, request flow ([`docs/diagrams/request-flow.png`](docs/diagrams/request-flow.png)), threat model, evaluation plan and roadmap.

## Status

| Phase | | |
|---|---|---|
| 1 | Foundations: config, Postgres + pgvector, migrations, CI | ✅ |
| 2 | Data: fictional multi-utility dataset, HSE guidance, Docling ingestion | ✅ |
| 3 | Retrieval: hybrid search, row-level security, reranking | ✅ |
| 4 | Workflow: guardrails, safety tiers, cited answers, approvals, audit | ✅ |
| 5 | Chainlit UI with personas | ✅ |
| 6 | Evaluation: golden and red-team sets, release gates, LangSmith tracing | ✅ |
| 7 | Deployment: container image and GitHub Actions | ✅ image builds; hosting not yet chosen |
| 8 | Governance documents | ✅ |

## Quickstart

Needs [uv](https://docs.astral.sh/uv/) and Docker.

```sh
cp .env.example .env          # add your keys
docker compose up -d db       # Postgres 17 + pgvector
uv sync --all-extras          # extras: ingest (Docling) and offline (local reranker)
uv run gigawhat db upgrade
uv run gigawhat doctor        # shows what's ready and what's missing

uv run gigawhat data fetch-hse      # download public HSE guidance (fetched, not redistributed)
uv run gigawhat data ingest         # parse, chunk and embed every document in the register
uv run gigawhat data load-records   # sites, assets, work orders, inspections, incidents, alarms
uv run gigawhat data docs           # every stored version with its status and review date
```

The first `ingest` downloads Docling's PDF layout models and takes a few minutes; later runs skip anything already stored. For the offline profile, run `ollama pull qwen3-embedding:0.6b` first.

The fictional procedures are published as PDFs, like a document management system would hold them. Each PDF is printed from the Markdown file beside it. After editing a procedure's Markdown, publish it again with `uv run scripts/render_procedures.py` (it prints with Google Chrome through Playwright and installs its own dependencies); a test fails until you do.

## Run it

```sh
uv run uvicorn gigawhat.api:app --port 8000   # chat UI at http://localhost:8000
uv run gigawhat ask "How do I purge the 75 mbar main on Mill Lane?" --persona gas_field_engineer
uv run gigawhat search "vent stack height" --persona gas_field_engineer
```

Pick a persona at the top of the chat; each opens on its own welcome and example questions, and the **Readme** button explains every status a reply can have. Safety-critical questions wait for an Authorised Person: switch to the Authorised Person persona for the same business unit to release or decline them, then switch back to see the outcome. The Auditor persona shows this browser's audit trail.

On the offline profile, answers take 20 seconds to a minute on a laptop; on the cloud profile, about 10 seconds.

The look lives outside the Python code: colours in [`public/theme.json`](public/theme.json), the logo, persona and question icons in [`public/`](public), a few touches in [`public/style.css`](public/style.css), and GigaWhat's own wording for Chainlit's labels in `.chainlit/translations/en-US.json`. How replies are framed (status lines, notice boxes, approval cards) is in [`src/gigawhat/ui/presentation.py`](src/gigawhat/ui/presentation.py). Icons are from [Lucide](https://lucide.dev) (ISC licence, [`public/icons/LICENSE-lucide.txt`](public/icons/LICENSE-lucide.txt)).

## Container

`docker build -t gigawhat .` builds the image: cloud profile only, no PyTorch or Docling. On an Apple M4 Mac, run it with `-e OPENSSL_armcap=0`: Linux VMs on M4 advertise CPU features that crash OpenSSL's start-up probe. Graviton and x86 servers don't need it.

## Data

[`data/README.md`](data/README.md) describes GigaWhat Energy, the fictional utility: its sites, assets, roles and document register, plus the deliberate test cases (superseded and draft procedures, an overdue review, two procedures that conflict) that the assistant must handle correctly.

## Profiles

Set `GIGAWHAT_PROFILE` in `.env`:

| Profile | Models | Needs |
|---|---|---|
| `cloud` (default) | Gemini's free tier for both chat roles, OpenAI for embeddings, Cohere for reranking (or the local reranker with `GIGAWHAT_RERANKER=local`) | `GOOGLE_API_KEY`, `OPENAI_API_KEY`, and `COHERE_API_KEY` unless reranking locally |
| `offline` | `gpt-oss:20b` and Qwen3 embeddings on [Ollama](https://ollama.com), and the local reranker. Nothing leaves your machine. | Ollama running locally |

Each profile has its own database (`gigawhat_cloud`, `gigawhat_offline`) because the two embedding models produce different vectors.

Models are chosen by role in [`src/gigawhat/providers/registry.py`](src/gigawhat/providers/registry.py):

| Role | Does | Cloud default |
|---|---|---|
| fast | Input check, safety tier, search rewrites | `gemini:gemini-3.1-flash-lite` |
| answer | Gathering records and writing cited answers | `gemini:gemini-3.5-flash-lite` |
| embeddings | Search vectors | `openai:text-embedding-3-small` |
| reranker | Scoring passages against the question | `cohere:rerank-v3.5`, or local `BAAI/bge-reranker-v2-m3` |

The two chat roles use different Gemini models because free-tier quotas are per model: each gets its own 15 requests a minute and 500 a day. Switch a chat role in `.env` with `GIGAWHAT_FAST_MODEL` or `GIGAWHAT_ANSWER_MODEL`, written `provider:model` (`gemini`, `groq` or `ollama`), for example when a model's daily quota is used up. `gigawhat doctor` checks each role's key and model, shows its rate limits, and checks that the answer model's tokens-a-minute limit fits an evidence request.

## Code layout

`src/gigawhat/` is split into layers ([`docs/phase-1-architecture.md`](docs/phase-1-architecture.md), section 5). Dependencies point inwards: the interface uses orchestration, which uses the layers below it.

| Layer | Does |
|---|---|
| `api.py`, `ui/`, `cli.py` | The interfaces: HTTP, the Chainlit chat and the command line |
| `orchestration/` | The LangGraph workflow (`graph.py`), the service the interfaces call (`service.py`) and the responses it returns |
| `identity/` | Personas: who is asking and what they may see or release |
| `policy/` | Safety tiers and their rules, the input guardrail, personal-data masking |
| `retrieval/` | Hybrid search under row-level security, reranking |
| `records/` | Read-only record tools and the agent that picks them |
| `generation/` | Search rewrites and drafting cited answers |
| `validation/` | Named checks on every draft before it is shown |
| `oversight/` | Approvals, the append-only audit trail, feedback |
| `providers/` | Models by role, their limits and pacing |
| `ingestion/` | The document register, parsing, chunking and embedding |
| `storage/` | Database engine, schema and migrations |
| `observability/` | Structured JSON logs and LangSmith tracing |
| `evaluation/` | Cases, checks, release gates, LangSmith experiments |
| `prompts.py` | Every prompt; `PROMPT_VERSION` is their fingerprint |

## Development

```sh
uv run pytest                 # unit + integration tests (integration needs the db container)
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## Evaluation

```sh
uv run gigawhat eval run --suite golden --suite redteam          # writes evals/reports/<date>-<profile>-....md
uv run gigawhat eval run --suite golden --limit 10 --judge        # also scores answers with DeepEval
```

With a LangSmith key on the cloud profile, each run is also a LangSmith experiment: the cases are synced to the `gigawhat-evaluation` dataset, every case's trace is kept with its scores, and the release gates are summary scores, so runs can be compared side by side. On the offline profile, or without a key, it runs on this machine only. A full run uses about half of each Gemini model's daily free quota; `--judge` adds DeepEval calls to the answer model's.

60 golden questions and 25 red-team attacks, scored in code against five release gates (never cite a forbidden version, every emergency gets the emergency card, no generated answer to a safety-critical question, no personal data repeated, no case failed to run) and five quality targets. The command exits non-zero if a gate fails. The method and the latest results are in [`docs/governance/evaluation-report.md`](docs/governance/evaluation-report.md).

## Governance

[`docs/governance/`](docs/governance/README.md) holds the system card, risk register, human-oversight design, data-protection assessment, change control, regulatory alignment and evaluation report, each pointing to the code and tests that back its claims, and listing the gaps that remain.

## Licence

[Apache-2.0](LICENSE)
