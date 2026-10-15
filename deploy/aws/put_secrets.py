# /// script
# requires-python = ">=3.12"
# dependencies = ["boto3[crt]>=1.41", "python-dotenv>=1"]
# ///
"""Copy the hosted app's API keys from .env to Parameter Store, and create its database password.

Each value is stored as a SecureString under /gigawhat/, which the server reads at deploy time.
Values are never printed. Run it again after changing a key in .env, then redeploy.

    uv run deploy/aws/put_secrets.py
"""

import secrets
from pathlib import Path

import boto3
from dotenv import dotenv_values

PROFILE = "gigawhat"
REGION = "eu-north-1"
PREFIX = "/gigawhat/"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
API_KEYS = ("GOOGLE_API_KEY", "OPENAI_API_KEY", "COHERE_API_KEY", "LANGSMITH_API_KEY")
DATABASE_PASSWORD = "GIGAWHAT_DATABASE_PASSWORD"


def main() -> None:
    env = dotenv_values(ENV_FILE)
    missing = [name for name in API_KEYS if not env.get(name)]
    if missing:
        raise SystemExit(f"Set these in {ENV_FILE} first: {', '.join(missing)}")

    ssm = boto3.Session(profile_name=PROFILE, region_name=REGION).client("ssm")
    for name in API_KEYS:
        ssm.put_parameter(Name=PREFIX + name, Value=env[name], Type="SecureString", Overwrite=True)
        print(f"Stored {PREFIX}{name}")

    # Postgres takes its password only when it first creates the database, so an existing
    # password is never replaced.
    try:
        ssm.put_parameter(
            Name=PREFIX + DATABASE_PASSWORD,
            Value=secrets.token_hex(24),
            Type="SecureString",
            Overwrite=False,
        )
        print(f"Created {PREFIX}{DATABASE_PASSWORD}")
    except ssm.exceptions.ParameterAlreadyExists:
        print(f"Kept the existing {PREFIX}{DATABASE_PASSWORD}")


if __name__ == "__main__":
    main()
