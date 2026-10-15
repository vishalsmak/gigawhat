# Hosting the demo on AWS

This folder puts the demo on a public HTTPS link. It is built for a demo, not for production: one small server, no high availability and no backups.

## What it builds

- One `t4g.small` server (2 vCPUs, 2 GB memory, arm64) running Ubuntu 24.04. Docker Compose runs the published image `ghcr.io/vishalsmak/gigawhat:main` and Postgres with pgvector (`compose.yaml`). Postgres listens on the server only.
- CloudFront in front, for the `https://….cloudfront.net` link. Nothing is cached. The server accepts HTTP only from CloudFront's addresses (`main.tf`).
- No SSH. Reach the server through Systems Manager.
- The API keys and the database password are SecureString parameters under `/gigawhat/` in Parameter Store. `put_secrets.py` puts them there, and `deploy.sh` reads them on the server. They never appear in this folder or in the Terraform state.

The server uses the Cohere reranker (`GIGAWHAT_RERANKER=cohere`): the local model needs more memory than the server has. Hosted questions are traced to the LangSmith project `gigawhat-hosted`, apart from runs on the Mac.

## Cost

Prices for `eu-north-1`, paid from the AWS project's credit:

| Item | Until 31 December 2026 | From January 2027 |
| --- | --- | --- |
| `t4g.small` server | free (AWS's `t4g.small` trial) | $12.56 a month |
| 20 GB gp3 disk | $1.67 a month | $1.67 a month |
| Public IPv4 address | $3.65 a month | $3.65 a month |
| CloudFront, Parameter Store | free tier | free tier |
| **Total** | **about $5.30 a month** | **about $17.90 a month** |

The server runs with standard CPU credits, so a busy spell slows it down rather than adding to the bill. The project's Free plan ends on 9 April 2027: run `terraform destroy` before then, or upgrade the project.

## Before you start

- Sign in: `aws login --region eu-north-1 --profile gigawhat`.
- Terraform 1.10 or later.
- The Session Manager plugin, for the data copy: `brew install --cask session-manager-plugin`.
- The keys in the repository's `.env`: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY` and `LANGSMITH_API_KEY`.
- The local `gigawhat_cloud` database, ingested and loaded (`docker compose up -d db`).

## Build it

Run these from the repository root.

1. Store the keys, so the server finds them when it first starts:

   ```sh
   uv run deploy/aws/put_secrets.py
   ```

2. Create everything (about five minutes, mostly CloudFront):

   ```sh
   terraform -chdir=deploy/aws init
   terraform -chdir=deploy/aws apply
   ```

3. Wait for the first boot to finish (about five more minutes). It installs Docker, pulls the images, runs the database migrations and starts the app. Check with:

   ```sh
   curl -s "$(terraform -chdir=deploy/aws output -raw url)/health"
   ```

4. Copy the documents and records from the Mac. Nothing is embedded again:

   ```sh
   deploy/aws/copy_data.sh
   ```

5. Open the link (`terraform -chdir=deploy/aws output -raw url`) and run a few questions from the demo script.

## Day to day

Run a command on the server, for example to deploy a new image after CI has published it:

```sh
aws ssm send-command --profile gigawhat --region eu-north-1 \
  --instance-ids "$(terraform -chdir=deploy/aws output -raw instance_id)" \
  --document-name AWS-RunShellScript --parameters commands=/opt/gigawhat/deploy.sh
```

`deploy.sh` reads the parameters again, pulls the newest image and restarts whatever changed. Use it after any of these:

- **New image:** push to `main` and wait for the `Image` workflow.
- **New key:** change `.env`, then `uv run deploy/aws/put_secrets.py`.
- **Pause the demo:** `aws ssm put-parameter --profile gigawhat --region eu-north-1 --name /gigawhat/GIGAWHAT_PAUSED --type String --value true --overwrite`. Set it to `false` to resume.

Open a shell on the server, for example to read the logs:

```sh
aws ssm start-session --profile gigawhat --region eu-north-1 \
  --target "$(terraform -chdir=deploy/aws output -raw instance_id)"
cd /opt/gigawhat && sudo docker compose logs app --tail 50
```

The first boot's log is `/var/log/cloud-init-output.log`.

## Things to know

- **The database lives on the server's disk.** Terraform ignores newer Ubuntu images and edits to `cloud-init.yaml`, so the server is never replaced by accident. Changes to `compose.yaml` or `cloud-init.yaml` reach the server only if it is rebuilt: `terraform apply -replace=aws_instance.app`, then `copy_data.sh` again.
- **Everyone shares the free model quotas:** Gemini allows 500 requests a day per model, and the Cohere trial about 1,000 reranks a month. Each browser may ask 30 questions an hour (`GIGAWHAT_QUESTIONS_PER_HOUR`, enforced by `src/gigawhat/ui/limits.py`).
- **CloudFront talks to the server over plain HTTP.** Visitors' connections to CloudFront are HTTPS. The data is fictional, so the last hop isn't encrypted; a real deployment would add a certificate at the server or a private origin.
- **The visitor cookie has no `Secure` flag here.** The app sets it only when the request arrives as HTTPS (`src/gigawhat/api.py`), and CloudFront removes `X-Forwarded-Proto` from every request it forwards, even as a custom origin header. Visitors still reach the app only over HTTPS: CloudFront redirects plain HTTP.
- **The Systems Manager policy lets the server read any parameter in the account**, not just `/gigawhat/`. This account holds only GigaWhat's.

## Remove it

```sh
terraform -chdir=deploy/aws destroy
```

This deletes the server, its disk and the database with it. The parameters under `/gigawhat/` stay until you delete them in the Parameter Store console.
