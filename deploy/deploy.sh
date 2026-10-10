#!/usr/bin/env bash
# Runs on the server (from user data on first boot, then through SSM for each release):
# refreshes secrets, pulls the image, migrates, seeds an empty database, and restarts.
set -euo pipefail
cd /opt/gigawhat

export GIGAWHAT_IMAGE_TAG="${1:-main}"
COMPOSE="docker compose -f docker-compose.prod.yml"
DATA_TABLES="documents document_versions chunks sites assets work_orders inspections incidents alarms"

# Compose reads .env itself for both substitution and the app's environment; it is never sourced
# into this shell, where a secret containing $ or spaces would be misread.
./fetch-env.sh

$COMPOSE pull
$COMPOSE up -d db
$COMPOSE run --rm app gigawhat db upgrade

chunks=$($COMPOSE exec -T db psql -U gigawhat -d gigawhat_cloud -Atc "SELECT count(*) FROM chunks")
if [ "$chunks" = "0" ]; then
  account=$(aws sts get-caller-identity --query Account --output text)
  if aws s3 cp "s3://gigawhat-seed-${account}/gigawhat_cloud.dump" /tmp/seed.dump; then
    $COMPOSE exec -T db pg_restore -U gigawhat -d gigawhat_cloud --data-only --disable-triggers \
      < /tmp/seed.dump
    rm -f /tmp/seed.dump
    echo "Seeded the database from the uploaded dump."
  else
    echo "Database is empty and no seed dump was found; run deploy/seed.sh from a workstation."
  fi
fi

$COMPOSE up -d --remove-orphans
docker image prune -f >/dev/null
echo "Deployed ${GIGAWHAT_IMAGE_TAG}."
