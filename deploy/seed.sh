#!/usr/bin/env bash
# Run on a workstation: builds the cloud-profile database locally (Docling + Cohere embeddings),
# then uploads a data-only dump that the server restores on its next deploy.
# Needs: docker compose up -d db, COHERE_API_KEY in .env, and the AWS profile for the project.
set -euo pipefail
AWS_PROFILE="${AWS_PROFILE:-gigawhat}"
export GIGAWHAT_PROFILE=cloud

uv run gigawhat db upgrade
uv run gigawhat data fetch-hse
uv run gigawhat data ingest
uv run gigawhat data load-records

tables=(documents document_versions chunks sites assets work_orders inspections incidents alarms)
docker compose exec -T db pg_dump -U gigawhat -Fc --data-only "${tables[@]/#/-t}" gigawhat_cloud \
  > /tmp/gigawhat_cloud.dump

account=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
aws s3 cp /tmp/gigawhat_cloud.dump "s3://gigawhat-seed-${account}/gigawhat_cloud.dump" \
  --profile "$AWS_PROFILE"
echo "Uploaded. Run the deploy workflow (or deploy.sh on the server) to restore it."
