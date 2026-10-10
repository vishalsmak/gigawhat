# GigaWhat

An AI assistant that helps operational staff at a gas and electricity utility find the approved procedure for a job, see the evidence behind it, and get suggested next steps. People make the decisions: GigaWhat never decides anything safety-critical, and it has no connection to plant or OT systems.

This is a reference implementation built to production standards and run as a demo. The utility, its procedures and its records are fictional. Public HSE guidance is downloaded by a script, not redistributed.

See [`docs/architecture.html`](docs/architecture.html) for how it works: components, safety tiers, retrieval, guardrails and hosting.

## Status

| Phase | | |
|---|---|---|
| 1 | Foundations: config, Postgres + pgvector, migrations, CI | ✅ |
| 2 | Data: fictional multi-utility dataset, HSE guidance, Docling ingestion | ✅ |
| 3 | Retrieval: hybrid search, row-level security, reranking | ✅ |
| 4 | Workflow: guardrails, safety tiers, cited answers, approvals, audit | ✅ |
| 5 | Chainlit UI with personas | ✅ |
| 6 | Evaluation: golden and red-team sets, release gates, Langfuse tracing | ✅ |
| 7 | Deployment: container, Terraform for AWS, GitHub Actions | ✅ code ready, not yet deployed |
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

## Run it

```sh
uv run uvicorn gigawhat.api:app --port 8000   # chat UI at http://localhost:8000
uv run gigawhat ask "How do I purge the 75 mbar main on Mill Lane?" --persona gas_field_engineer
uv run gigawhat search "vent stack height" --persona gas_field_engineer
```

Pick a persona at the top of the chat. Safety-critical questions wait for an Authorised Person: switch to the Authorised Person persona for the same business unit to release or decline them, then switch back to see the outcome. The Auditor persona shows this browser's audit trail.

On the offline profile, answers take about a minute on a laptop; Claude on the cloud profile is much faster.

## Container

`docker build -t gigawhat .` builds the hosted image: cloud profile only, no PyTorch or Docling. On an Apple M4 Mac, run it with `-e OPENSSL_armcap=0`: Linux VMs on M4 advertise CPU features that crash OpenSSL's start-up probe. Graviton and x86 servers don't need it.

Deployment to AWS is described in [`infra/README.md`](infra/README.md).

## Data

[`data/README.md`](data/README.md) describes Harrowmere Energy, the fictional utility: its sites, assets, roles and document register, plus the deliberate test cases (superseded and draft procedures, an overdue review, two procedures that conflict) that the assistant must handle correctly.

## Profiles

Set `GIGAWHAT_PROFILE` in `.env`:

| Profile | Models | Needs |
|---|---|---|
| `cloud` (default) | Claude for answers, Cohere for embeddings and reranking. The hosted demo uses this. | `ANTHROPIC_API_KEY`, `COHERE_API_KEY` |
| `offline` | Open models on [Ollama](https://ollama.com). Nothing leaves your machine. | Ollama running locally |

Each profile has its own database (`gigawhat_cloud`, `gigawhat_offline`) because the two embedding models produce different vectors.

## Development

```sh
uv run pytest                 # unit + integration tests (integration needs the db container)
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
```

## Evaluation

```sh
uv run gigawhat eval run --suite golden --suite redteam          # writes evals/reports/<date>-<profile>-....md
uv run gigawhat eval run --suite golden --limit 10 --judge        # also scores answers with DeepEval
```

60 golden questions and 25 red-team attacks, scored in code against five release gates (never cite a forbidden version, every emergency gets the emergency card, no generated answer to a safety-critical question, no personal data repeated, no case failed to run) and five quality targets. The command exits non-zero if a gate fails. The method and the latest results are in [`docs/governance/evaluation-report.md`](docs/governance/evaluation-report.md).

## Governance

[`docs/governance/`](docs/governance/README.md) holds the system card, risk register, human-oversight design, data-protection assessment, change control, regulatory alignment and evaluation report, each pointing to the code and tests that back its claims, and listing the gaps that remain.

## Licence

[Apache-2.0](LICENSE)
