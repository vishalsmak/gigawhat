#!/bin/sh
# Copies the corpus and the operational records from this Mac's gigawhat_cloud database into the
# server's, through a Systems Manager port forward. Nothing is embedded again. The audit trail,
# approvals, feedback and checkpoints stay behind. The server's tables must be empty: the copy
# runs in one transaction and stops at the first error.
#
#   deploy/aws/copy_data.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
tunnel_port=15432
tables="documents document_versions chunks sites assets work_orders inspections incidents alarms"

instance=$(terraform -chdir="$here" output -raw instance_id)
PGPASSWORD=$(aws ssm get-parameter --profile gigawhat --region eu-north-1 \
    --name /gigawhat/GIGAWHAT_DATABASE_PASSWORD --with-decryption \
    --query Parameter.Value --output text)
export PGPASSWORD

# The tunnel runs in its own process group (set -m): it is the aws command plus its
# session-manager-plugin child, and stopping the group stops both without signalling this script.
tunnel_log=$(mktemp)
set -m
aws ssm start-session --profile gigawhat --region eu-north-1 --target "$instance" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "portNumber=5432,localPortNumber=$tunnel_port" >/dev/null 2>"$tunnel_log" &
tunnel=$!
set +m
trap 'kill -- -$tunnel 2>/dev/null; rm -f "$tunnel_log"' EXIT

waited=0
until nc -z 127.0.0.1 "$tunnel_port" 2>/dev/null; do
    if ! kill -0 "$tunnel" 2>/dev/null || [ "$waited" -ge 30 ]; then
        echo "The tunnel to $instance didn't open:" >&2
        cat "$tunnel_log" >&2
        exit 1
    fi
    sleep 1
    waited=$((waited + 1))
done

table_options=""
for table in $tables; do
    table_options="$table_options --table=$table"
done

# The local Postgres container has pg_dump and psql; it reaches the tunnel on the Mac through
# host.docker.internal.
docker compose --project-directory "$repo" exec -T -e PGPASSWORD db sh -c "
    pg_dump -U gigawhat -d gigawhat_cloud --data-only $table_options |
    psql --quiet -v ON_ERROR_STOP=1 --single-transaction \
        -h host.docker.internal -p $tunnel_port -U gigawhat -d gigawhat_cloud >/dev/null"

for table in $tables; do
    count=$(docker compose --project-directory "$repo" exec -T -e PGPASSWORD db psql -At \
        -h host.docker.internal -p $tunnel_port -U gigawhat -d gigawhat_cloud \
        -c "SELECT count(*) FROM $table")
    echo "$table: $count rows on the server"
done
