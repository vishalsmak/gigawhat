data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  log_group  = "/ecs/${var.name}"
}

# --- Encryption key --------------------------------------------------------------------------------

# One customer-managed key for the database, its snapshots, secrets and logs, so access to the data
# can be audited and revoked in one place.
data "aws_iam_policy_document" "kms" {
  statement {
    sid       = "AccountAdministersKeyThroughIam"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${local.partition}:iam::${local.account_id}:root"]
    }
  }

  statement {
    sid = "CloudWatchLogsEncryptsOurLogGroups"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = ["arn:${local.partition}:logs:${var.region}:${local.account_id}:log-group:*"]
    }
  }
}

resource "aws_kms_key" "main" {
  description             = "${var.name}: database, secrets and logs"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.kms.json
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.name}"
  target_key_id = aws_kms_key.main.key_id
}

# --- Secrets -----------------------------------------------------------------------------------------

# App secrets as one JSON secret with keys COHERE_API_KEY, LANGFUSE_PUBLIC_KEY and
# LANGFUSE_SECRET_KEY (empty strings are fine for Langfuse). Terraform creates only the container;
# the value is set with `aws secretsmanager put-secret-value` so it never reaches Terraform state.
# No Anthropic key: Claude is called through Bedrock with the task role.
resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.name}/app"
  description             = "GigaWhat app API keys"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 30
}

# --- Database ----------------------------------------------------------------------------------------

# pgvector ships with RDS for PostgreSQL 17 and is enabled per database by the app's migrations
# (CREATE EXTENSION vector); it needs no preload. The parameters below tune for it and harden TLS.
resource "aws_db_parameter_group" "postgres17" {
  name        = "${var.name}-postgres17"
  family      = "postgres17"
  description = "GigaWhat: TLS only, statement stats, room for HNSW index builds"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  # In kB: 512 MB for building pgvector HNSW indexes without spilling to disk.
  parameter {
    name  = "maintenance_work_mem"
    value = "524288"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

# Created up front so RDS log exports get a retention period instead of "never expire".
resource "aws_cloudwatch_log_group" "postgres" {
  name              = "/aws/rds/instance/${var.name}/postgresql"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.main.arn
}

resource "aws_db_instance" "main" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = "17"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage_gb
  max_allocated_storage = var.db_max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.main.arn

  db_name  = "gigawhat_cloud"
  username = "gigawhat"
  # RDS generates the password and keeps it, rotated, in Secrets Manager. ECS reads it at task
  # start, so force a new ECS deployment after each rotation (or have the app fetch it on connect).
  manage_master_user_password   = true
  master_user_secret_kms_key_id = aws_kms_key.main.key_id

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  parameter_group_name   = aws_db_parameter_group.postgres17.name

  backup_retention_period   = var.db_backup_retention_days
  backup_window             = "01:00-02:00"
  maintenance_window        = "sun:02:30-sun:03:30"
  copy_tags_to_snapshot     = true
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.name}-final"

  auto_minor_version_upgrade      = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  depends_on = [aws_cloudwatch_log_group.postgres]
}
