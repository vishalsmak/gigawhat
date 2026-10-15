#!/bin/sh
# Starts or updates the demo on the server: writes .env from Parameter Store, pulls the newest
# image and restarts whatever changed. Runs at first boot, then through Systems Manager.
set -eu
export PATH="$PATH:/snap/bin"
cd /opt/gigawhat
umask 077
region=$(cloud-init query v1.region)

# Retried because a new server's permissions can take a minute to reach IAM. IAM checks the
# path exactly as given, so no trailing slash.
attempt=1
until parameters=$(aws ssm get-parameters-by-path --region "$region" --path /gigawhat \
    --with-decryption --query 'Parameters[].[Name,Value]' --output text); do
    if [ "$attempt" -ge 10 ]; then
        echo "Couldn't read Parameter Store; .env is unchanged." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 15
done
if [ -z "$parameters" ]; then
    echo "Nothing under /gigawhat in Parameter Store; run put_secrets.py. .env is unchanged." >&2
    exit 1
fi

# Single quotes stop Compose from expanding anything inside a value.
printf '%s\n' "$parameters" |
    awk -F '\t' '{ sub("^/gigawhat/", "", $1); printf "%s=\047%s\047\n", $1, $2 }' > .env.new
mv .env.new .env

docker compose pull --quiet
docker compose up --detach --remove-orphans
docker image prune --force
