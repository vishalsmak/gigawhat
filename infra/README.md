# Infrastructure

Terraform for hosting GigaWhat on AWS. Everything is created in your project's single Region (`eu-north-1` by default); nothing goes in `us-east-1`.

| Module | What it is for | Rough cost per month |
|---|---|---|
| [`terraform/lean`](terraform/lean) | The hosted demo. One Graviton EC2 instance running the app, Postgres and Caddy in Docker, with a free `sslip.io` HTTPS hostname. | About $18 (see below) |
| [`terraform/github-deploy`](terraform/github-deploy) | Optional. Lets GitHub Actions on `main` redeploy the lean instance, with no stored AWS keys. | Free |
| [`terraform/production-reference`](terraform/production-reference) | Not deployed. What a regulated company would run instead: private VPC, Multi-AZ RDS, ECS Fargate behind a load balancer and WAF, Claude on Bedrock. It is only checked with `terraform validate`. | Indicative only: several hundred dollars, an order of magnitude more than lean, mostly the Multi-AZ database and NAT gateways |

Lean, broken down (on-demand prices, check the [AWS Pricing Calculator](https://calculator.aws/) for today's figures):

| Item | About |
|---|---|
| `t4g.small` instance, running all month | $12 |
| 20 GB encrypted gp3 root volume | $1.70 |
| Public IPv4 address (the Elastic IP) | $3.65 |
| 7 daily snapshots (incremental) and the seed bucket | $1 or less |
| **Total** | **$15 to $20** |

Anthropic and Cohere bill their API usage separately; it is not part of the AWS bill. At about $18 a month, $100 of AWS credit lasts roughly five months.

## Before you start

1. **Confirm your project's Region** in AWS Settings > View all projects > Overview > Additional Info > Region. If it isn't `eu-north-1`, set `region` in `terraform.tfvars` and use that Region in every command below.
2. **Upgrade from the Free plan to the Paid plan before 9 April 2027**, or the account is closed. You do this in AWS Settings.
3. **Set a spend limit** in AWS Settings > Billing. If spending reaches it, the project is paused and everything returns "Access Denied" until you raise it. Only the project owner can change it.
4. Install [Terraform](https://developer.hashicorp.com/terraform/install) 1.6 or later, AWS CLI v2 and the Session Manager plugin (`brew install --cask session-manager-plugin`), then sign in with `aws login`.
5. The Region needs its **default VPC**. New projects have one; if it was deleted, run `aws ec2 create-default-vpc`.

## Deploy the lean hosting

Run everything from the repository root unless a step says otherwise.

```sh
export AWS_REGION=eu-north-1
```

### 1. Store the settings and secrets in Parameter Store

The instance reads every parameter under `/gigawhat/` into `/opt/gigawhat/.env` when it starts. Terraform never creates or sees them, so they are not in Terraform state.

```sh
read -rsp 'Anthropic API key: ' ANTHROPIC_API_KEY; echo
read -rsp 'Cohere API key: ' COHERE_API_KEY; echo

aws ssm put-parameter --name /gigawhat/ANTHROPIC_API_KEY --type SecureString --value "$ANTHROPIC_API_KEY"
aws ssm put-parameter --name /gigawhat/COHERE_API_KEY --type SecureString --value "$COHERE_API_KEY"
aws ssm put-parameter --name /gigawhat/GIGAWHAT_DATABASE_PASSWORD --type SecureString --value "$(openssl rand -hex 24)"
aws ssm put-parameter --name /gigawhat/GIGAWHAT_PROFILE --type String --value cloud

# Optional: Langfuse tracing
read -rsp 'Langfuse public key: ' LANGFUSE_PUBLIC_KEY; echo
read -rsp 'Langfuse secret key: ' LANGFUSE_SECRET_KEY; echo
aws ssm put-parameter --name /gigawhat/LANGFUSE_PUBLIC_KEY --type SecureString --value "$LANGFUSE_PUBLIC_KEY"
aws ssm put-parameter --name /gigawhat/LANGFUSE_SECRET_KEY --type SecureString --value "$LANGFUSE_SECRET_KEY"
```

Reading the keys with `read -s` keeps them out of your shell history. Values must fit on one line; avoid `$` and quotes in them (the generated database password is hex, so it is safe). To change a value later, run the same command with `--overwrite`.

`GIGAWHAT_DOMAIN` is optional. If it isn't set, the instance uses its own `sslip.io` hostname. Set it only if you point your own domain at the Elastic IP:

```sh
aws ssm put-parameter --name /gigawhat/GIGAWHAT_DOMAIN --type String --value gigawhat.example.com
```

The database password takes effect only when Postgres first creates its data volume. Changing the parameter afterwards does not change the password inside the database.

### 2. Make the container image public

The instance pulls the app image from GitHub Container Registry with no GitHub credentials. On GitHub, open the repository's **Packages** > the `gigawhat` package > **Package settings** > **Change visibility** > **Public**. GHCR packages start private even when the repository is public.

Keeping it private would mean storing a GitHub token on the instance (another secret in Parameter Store, plus `docker login ghcr.io` in the deploy script) and rotating it. The code is already public under Apache-2.0 and the image contains no secrets, so public is simpler and no less safe.

The image must include a `linux/arm64` build, because the instance is Graviton.

### 3. Create the infrastructure

```sh
cd infra/terraform/lean
cp terraform.tfvars.example terraform.tfvars   # optional: every value has a default
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform output
```

The instance then installs Docker, downloads `docker-compose.prod.yml`, `Caddyfile` and `deploy.sh` from the repository's `deploy/` folder and starts the app. This takes about five minutes. To watch it:

```sh
$(terraform output -raw ssm_connect_command)
sudo tail -f /var/log/cloud-init-output.log    # finished when it prints "== Done"
```

### 4. Seed the database

Back in the repository root, make a dump of your local, fully ingested database and upload it to the seed bucket (objects are deleted automatically after 30 days):

```sh
docker compose exec -T db pg_dump -U gigawhat -Fc gigawhat_cloud > gigawhat_cloud.dump
aws s3 cp gigawhat_cloud.dump "s3://$(terraform -chdir=infra/terraform/lean output -raw seed_bucket)/gigawhat_cloud.dump"
```

Then restore it on the instance, in a Session Manager shell:

```sh
sudo -i
cd /opt/gigawhat
aws s3 cp --region eu-north-1 "s3://gigawhat-seed-<account_id>/gigawhat_cloud.dump" /tmp/
docker compose -f docker-compose.prod.yml exec -T db \
  pg_restore -U gigawhat -d gigawhat_cloud --clean --if-exists --no-owner < /tmp/gigawhat_cloud.dump
rm /tmp/gigawhat_cloud.dump
```

### 5. Open it

```sh
terraform -chdir=infra/terraform/lean output -raw url
```

The first visit can take a minute while Caddy gets a Let's Encrypt certificate for the `sslip.io` name.

## Update

New app release, changed deploy files, or a changed parameter: run the update script on the instance. It downloads the `deploy/` files again, rebuilds `.env` from Parameter Store and runs `deploy.sh`.

```sh
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --targets Key=tag:Project,Values=gigawhat \
  --parameters 'commands=["/opt/gigawhat/update.sh"]' \
  --comment "Update GigaWhat"
```

Or from a Session Manager shell: `sudo /opt/gigawhat/update.sh`.

Terraform changes: `terraform plan` and `terraform apply` as usual. Terraform deliberately ignores newer AMIs and changes to the bootstrap script, because replacing the instance deletes the database on its root volume. If you do want a fresh instance, run `terraform apply -replace=aws_instance.app` and seed the database again (or restore a snapshot).

Operating system patches: `sudo dnf upgrade --releasever=latest -y`, then `sudo reboot`. The app restarts with Docker.

### Deploy from GitHub Actions (optional)

```sh
cd infra/terraform/github-deploy
terraform init && terraform apply
terraform output -raw role_arn
```

If the account already has a GitHub OIDC provider, add `-var create_oidc_provider=false`. The role trusts only `vishalsmak/gigawhat` on `refs/heads/main`; the name must match GitHub's casing exactly. In the workflow, grant `permissions: id-token: write`, use `aws-actions/configure-aws-credentials` with `role-to-assume` set to that ARN, then run the `send-command` above.

## Destroy

```sh
cd infra/terraform/lean
terraform destroy
```

This deletes the instance and its root volume (the database and Docker images with it), the Elastic IP, the security group, the IAM roles and instance profile, the snapshot policy, and the seed bucket with its contents.

It does not delete:

- **Snapshots** already taken. Deleting the policy leaves them behind, and they keep costing a little:
  ```sh
  aws ec2 describe-snapshots --owner-ids self --filters Name=tag:SnapshotPolicy,Values=gigawhat-daily \
    --query 'Snapshots[].SnapshotId' --output text | xargs -n1 aws ec2 delete-snapshot --snapshot-id
  ```
- **The Parameter Store parameters**, which Terraform never managed:
  ```sh
  aws ssm get-parameters-by-path --path /gigawhat --query 'Parameters[].Name' --output text \
    | xargs aws ssm delete-parameters --names
  ```
- **The GitHub deploy role**, if you created it: `terraform destroy` in `terraform/github-deploy`.

## Security notes

- **No SSH.** There is no key pair and port 22 is closed. Administration is through Session Manager, which connects outwards from the instance; every session start is recorded in CloudTrail.
- **IMDSv2 only**, with a hop limit of 1, so containers can't reach the instance's AWS credentials. Only the host scripts use AWS.
- **Secrets live only in Parameter Store** as SecureStrings. They are not in user data, Terraform state or Git. On the instance they exist only in `/opt/gigawhat/.env` (root-only, mode 600) on an encrypted volume.
- **Least-privilege roles.** The instance may read `/gigawhat/*` parameters, decrypt them only through Parameter Store, and read the seed bucket. The snapshot role and the GitHub role are limited to their own job, with conditions on who can assume them. One caveat: the AWS managed `AmazonSSMManagedInstanceCore` policy, which Session Manager needs, also allows reading any parameter in the account, so keep this project for GigaWhat only.
- **The GitHub role can run shell commands as root on the instance**, so anyone who can push to `main` effectively can too. Protect the branch.
- **Storage:** the root volume and its snapshots are encrypted; the seed bucket blocks all public access, requires TLS and encrypts objects.
- **CPU credits** are set to `standard`, so the instance slows down under sustained load rather than running up surplus-credit charges.
- **`sslip.io`** is a free third-party DNS service. It is fine for a demo; use your own domain for anything real.
- There is no WAF in front of the lean instance; the app's own per-visitor question limit is the throttle. The production reference adds AWS WAF.

## Terraform state

State is kept locally in each module directory and is git-ignored. It contains resource IDs and account details but no secrets. A team would keep state in an S3 bucket with locking (`use_lockfile = true`), so that two people can't apply at once; each `versions.tf` shows where that goes.
