data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition

  parameter_path_arn = "arn:${local.partition}:ssm:${var.region}:${local.account_id}:parameter/gigawhat"
}

# --- Instance role -------------------------------------------------------------------------------

data "aws_iam_policy_document" "ec2_trust" {
  statement {
    sid     = "EC2AssumesInstanceRole"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    # IfExists: EC2 is not listed as supporting aws:SourceAccount for instance roles, and a plain
    # StringEquals on a missing key would deny the instance its credentials. This form still
    # rejects any request that does carry a different account.
    condition {
      test     = "StringEqualsIfExists"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "instance" {
  name                 = "gigawhat-instance"
  description          = "GigaWhat EC2 instance: Session Manager, read /gigawhat/* parameters, read the seed dump"
  assume_role_policy   = data.aws_iam_policy_document.ec2_trust.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "instance_runtime" {
  statement {
    sid = "ReadGigaWhatParameters"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    # GetParametersByPath is authorised against the path itself (parameter/gigawhat), so both ARNs
    # are needed.
    resources = [
      local.parameter_path_arn,
      "${local.parameter_path_arn}/*",
    ]
  }

  statement {
    sid       = "DecryptSecureStringsViaSsmOnly"
    actions   = ["kms:Decrypt"]
    resources = ["arn:${local.partition}:kms:${var.region}:${local.account_id}:key/*"]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.region}.amazonaws.com"]
    }
  }

  statement {
    sid       = "ReadSeedDump"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.seed.arn}/*"]
  }
}

resource "aws_iam_role_policy" "instance_runtime" {
  name   = "gigawhat-runtime"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.instance_runtime.json
}

resource "aws_iam_instance_profile" "instance" {
  name = "gigawhat-instance"
  role = aws_iam_role.instance.name
}

# --- Data Lifecycle Manager role -----------------------------------------------------------------

data "aws_iam_policy_document" "dlm_trust" {
  statement {
    sid     = "DlmAssumesRole"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    # Wildcard policy ID: the lifecycle policy needs this role before it exists.
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${local.partition}:dlm:${var.region}:${local.account_id}:policy/*"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "gigawhat-dlm"
  description        = "Lets Data Lifecycle Manager snapshot the GigaWhat root volume"
  assume_role_policy = data.aws_iam_policy_document.dlm_trust.json
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}
