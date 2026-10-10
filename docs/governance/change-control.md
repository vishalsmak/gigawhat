# Change control

| | |
|---|---|
| Status | Draft for the demo. Harrowmere Energy is fictional. |
| Written against | Commit `3e8cb02` plus the follow-up fixes made on 10 October 2026 |
| Audience | Engineering, safety team, document controller, auditors |

This document says what is versioned, who should own each part, how a change reaches the hosted demo, which checks must pass first, and how to roll back. Where the repository does not enforce a step, it says so.

## 1. What is versioned

| Item | Where | Proposed owner | How it is recorded at run time | Checks |
|---|---|---|---|---|
| Prompts: tier classifier, input guardrail policy, evidence agent, answer writer | `src/gigawhat/assistant/prompts.py` (in `.github/CODEOWNERS`) | Engineering, with safety team review | `PROMPT_VERSION` in every audit event (`prompt_version` column, not nullable); shown in the Auditor view | Graph tests; full evaluation |
| Safety-tier rules | `src/gigawhat/assistant/safety_topics.yaml` (in `.github/CODEOWNERS`) | Electricity Safety Manager and Gas Safety Manager (stated in the file header) | Part of `PROMPT_VERSION`; matched rule IDs in each audit event (`guardrails.rules`) | `tests/test_tiers.py`; full evaluation |
| Guardrail policy | `INPUT_POLICY` in `prompts.py`; NeMo configuration built by `rails_config_yaml()` | Engineering, with safety team review | `INPUT_POLICY` is part of `PROMPT_VERSION`; block or allow in each audit event | Red-team set |
| Model names and settings | `src/gigawhat/models.py` | Engineering | `models` column in every audit event: chat, embeddings, reranker | Full evaluation on both profiles |
| Retrieval settings and thresholds | `src/gigawhat/retrieval/search.py` (`MIN_RELEVANCE`, `PASSAGES`, `CANDIDATES`), `src/gigawhat/assistant/responses.py` (`STRICT_EXTRACTS`), `src/gigawhat/retrieval/glossary.yaml` | Engineering | Not recorded | Retrieval tests; full evaluation |
| Personal-data masking | `src/gigawhat/assistant/pii.py` | Engineering, with DPO review | Entity types found, per event | `tests/test_pii.py`; red-team cases R022 to R025 |
| Document register | `data/corpus/register.yaml` (in `.github/CODEOWNERS`) and `data/corpus/procedures/`; HSE downloads pinned by `source_sha256` | Document controller | Citations name document, version and section; `document_versions` holds the content hash, embedding model and ingest time | `tests/test_register.py`, `tests/test_ingest.py`, `tests/test_project_data.py`, `tests/test_hse.py` |
| Operational records | `data/records/` | Records owners (fictional) | Record IDs cited in answers | `tests/test_records.py`, `tests/test_project_data.py` |
| Database schema | `src/gigawhat/migrations/versions/0001` to `0005` (Alembic) | Engineering | `alembic_version` table | `tests/test_database.py` |
| Evaluation sets | `evals/golden.yaml`, `evals/redteam.yaml` (in `.github/CODEOWNERS`) | Safety team and engineering | Reports in `evals/reports/` | `tests/test_evaluation.py::test_project_evaluation_sets_load` |
| Dependencies | `pyproject.toml`, `uv.lock` (with hashes) | Engineering | Not recorded | CI installs with `--locked` |
| Container image | `Dockerfile`; built by `.github/workflows/image.yml` | Engineering | Not recorded in the app | Image workflow |
| Infrastructure | `infra/terraform/lean`, `github-deploy`, `production-reference` | Engineering | Terraform state (local, git-ignored) | `terraform validate` (stated in `infra/README.md`) |

### The prompt fingerprint

`PROMPT_VERSION` is the first 12 hexadecimal characters of the SHA-256 of `TIER_PROMPT`, `INPUT_POLICY`, `EVIDENCE_PROMPT`, `ANSWER_PROMPT` and the text of `safety_topics.yaml` (`_fingerprint` in `prompts.py`). Any edit to those changes it, so every audit record shows which prompt and rule set produced it. At commit `3e8cb02` it is `01cc75222082`. To print it:

```sh
uv run python -c "from gigawhat.assistant.prompts import PROMPT_VERSION; print(PROMPT_VERSION)"
```

It does not cover the NeMo wrapper (`RAILS_CONFIG`), the glossary, the fixed response texts (emergency, refusal, abstain, strict preface), the retrieval thresholds or the masking rules. The audit trail also does not record the application version (Git commit or image tag). Adding the image's commit SHA to every audit event would close both gaps.

### The document register

The register, not the file, decides which version is current (`src/gigawhat/corpus/register.py`). It is validated on load: version numbers are unique, at most one version is approved, no superseded version is newer than the approved one, and approved procedures have an effective date.

**A published version can never be edited.** Ingestion stores a SHA-256 of each version's file. If a stored version's file changes, ingestion stops with `DocumentControlError`: "Issue a new version number instead of editing a published one." (`src/gigawhat/corpus/ingest.py`). Nothing is written (`tests/test_ingest.py::test_editing_a_published_version_is_refused`, `::test_refused_edit_leaves_database_untouched`). A new version and its predecessor's change to `superseded` are written in one transaction (`::test_new_version_supersedes_old_one`), and the database refuses two approved versions of one document (`::test_database_rejects_a_second_approved_version`).

This is why the conflict between PR-GAS-010 v4 and PR-GAS-021 v5 found while building the evaluation set stays in place until a new version resolves it (`data/README.md`).

Public HSE guidance is pinned the same way at download time: `gigawhat data fetch-hse` refuses a PDF whose SHA-256 differs from `source_sha256` in the register, with `ChecksumMismatchError` (`src/gigawhat/corpus/hse.py`; `tests/test_hse.py::test_refuses_a_download_that_does_not_match_the_registered_checksum`). A new HSE edition is adopted by reviewing it and updating the checksum.

Two caveats. `gigawhat data ingest --rebuild` deletes stored versions so they can be rebuilt. It is labelled development-only and now asks for confirmation, naming the database, but it can still be run against production. Status changes in the register (for example approved to withdrawn) are applied on the next ingest without any record of who made them beyond Git history.

## 2. How a change ships

| Step | What happens | Enforced by |
|---|---|---|
| 1 | Change made on a branch and opened as a pull request | Convention |
| 2 | CI runs: `uv sync --locked --all-extras`, `ruff check`, `ruff format --check`, `mypy`, `pytest` against a pgvector service container | `.github/workflows/ci.yml` on every pull request and push to `main` |
| 3 | For changes listed in section 3, the full evaluation is run and its report attached to the pull request | Convention. `.github/workflows/eval.yml` is run by hand. |
| 4 | Review and merge to `main` | `.github/CODEOWNERS` names owners for `safety_topics.yaml`, `prompts.py`, `register.yaml` and `evals/`. Their review is only required if branch protection is set to require code-owner review, which the repository cannot show. |
| 5 | The image is built for amd64 and arm64 from the commit CI tested and pushed to GitHub Container Registry as `main` and `sha-<7 characters>` | `.github/workflows/image.yml`, triggered by `workflow_run` only when CI completes successfully on `main`, or by hand |
| 6 | Someone runs the Deploy workflow with a tag (`main` or `sha-xxxxxxx`) | `.github/workflows/deploy.yml`, manual. It uses no GitHub environment, so its OIDC subject (`repo:<owner>/<repo>:ref:refs/heads/main`) matches the deploy role's trust policy in `infra/terraform/github-deploy/main.tf` |
| 7 | On the instance, `deploy.sh` refreshes `.env` from Parameter Store, pulls the image, starts Postgres, runs `gigawhat db upgrade`, seeds an empty database from S3 if needed, and restarts | `deploy/deploy.sh` through SSM Run Command |

Gaps in this path:

- Images are built only from commits that passed CI, but Deploy does not check that the evaluation passed for that commit. The release gates block a release only if people follow step 3.
- Running the Image workflow by hand skips the CI condition.
- Without a GitHub environment, Deploy has no required-reviewer step. Anyone who can run workflows on `main` can deploy, and the deploy role can run shell commands as root on the instance (stated in `infra/README.md`). Protect the branch and limit who can run workflows.

## 3. Which changes need what

| Change | Tests in CI | Full evaluation (golden and red-team, with judge) | Sign-off |
|---|---|---|---|
| Safety-tier rules (`safety_topics.yaml`) | Yes | Yes, on both profiles | Electricity Safety Manager and Gas Safety Manager |
| Prompts or guardrail policy | Yes | Yes, on both profiles | Engineering lead and safety team |
| Model name or model settings | Yes | Yes, on the affected profile | Engineering lead; DPO if the provider changes |
| Retrieval thresholds, chunking, glossary | Yes | Yes | Engineering lead |
| Masking rules | Yes | Red-team set at least | Engineering lead and DPO |
| New document version or status change in the register | Yes | Golden set at least, and any case naming that document | Document controller |
| Migration | Yes | Golden set at least | Engineering lead; auditor if it touches `audit_events` or `approvals` |
| User interface wording for approvals, emergencies or pauses | Yes | Not required | Safety team |
| Infrastructure | `terraform validate` and plan review | Not required | Engineering lead; security |

## 4. Release gates and quality targets

`gigawhat eval run` writes a report and exits with code 1 if any gate fails (`src/gigawhat/cli.py`). The five release gates, exactly as named in `src/gigawhat/evaluation/report.py`:

1. Never cites a forbidden version
2. Every emergency gets the emergency card
3. No generated answer to a safety-critical question
4. No personal data repeated
5. No case failed to run

Quality measures are tracked against targets but do not block a release:

| Measure | Target |
|---|---|
| Behaviour as expected | 85% |
| Safety tier as expected | 85% |
| Cites a required document | 85% |
| Red-team requests refused | 95% |
| Expected notices shown | 90% |
| Faithfulness (DeepEval) | 80% |
| Answer relevancy (DeepEval) | 80% |

The method is in [evaluation-report.md](evaluation-report.md).

## 5. Rollback

**Application.** Redeploy an earlier image tag. Run the Deploy workflow with that `sha-xxxxxxx` tag, or in a Session Manager shell run `sudo /opt/gigawhat/deploy.sh sha-xxxxxxx`. Images are kept in GitHub Container Registry; nothing in the repository deletes old tags.

**Database.** Migrations are forward-only in practice:

- The CLI offers `gigawhat db upgrade` and no downgrade command.
- The migration files do contain `downgrade()` functions, but running them is unsafe: downgrading `0005` drops `audit_events`, `approvals` and `feedback`, and with them the audit trail.
- `deploy.sh` runs `gigawhat db upgrade` with the image being deployed, under `set -e`. If the database is already at a revision that the older image does not know, Alembic is expected to stop with an unknown-revision error and the deploy will abort before the app restarts. Rolling back across a migration therefore does not work with the script as written.

So: roll back the image only between images with the same migration head. If a migration is wrong, fix forward with a new migration. Restoring an EBS snapshot (7 daily snapshots are kept) is the last resort, and it loses every audit event written since the snapshot. Record that loss.

**Deploy scripts.** `update.sh` downloads `deploy/` files from the `main` branch (`git_ref` in `infra/terraform/lean`), not from the image tag. Rolling back the image does not roll back `deploy.sh` or the compose file.

**Documents.** Never edit a published version to undo a change. Issue a new version, or change its status in the register and run `gigawhat data ingest`. The old version stays stored for audit questions.

**Safety-tier rules and prompts.** Revert the commit and redeploy. The audit trail shows which `PROMPT_VERSION` produced each answer before and after.

## 6. Records of change

| Question an auditor may ask | Where the answer is |
|---|---|
| Which prompts and rules produced this answer? | `audit_events.prompt_version`, matched against Git history |
| Which models? | `audit_events.models` |
| Which document versions? | `audit_events.sources` (document, version, section) and `document_versions` |
| Which application version? | Not recorded. Gap. |
| Who approved the change? | Pull request history on GitHub. Code owners are named in `.github/CODEOWNERS`; enforcement depends on branch protection. |
| Did the evaluation pass for this release? | The report artefact from the Evaluation workflow, if it was run. Not linked to the deployment. |
| Who deployed it, and when? | GitHub Actions run history for Deploy; SSM command history in AWS |
