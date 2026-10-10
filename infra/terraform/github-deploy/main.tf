# Lets a GitHub Actions workflow on main redeploy GigaWhat with Run Command, using short-lived
# OIDC credentials instead of stored access keys.

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  partition    = data.aws_partition.current.partition
  github_oidc  = "token.actions.githubusercontent.com"
  oidc_arn     = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn
  instance_arn = "arn:${local.partition}:ec2:${var.region}:${local.account_id}:instance/*"
}

# AWS verifies GitHub's certificate through its trusted CAs, so no thumbprint is needed.
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0

  url            = "https://${local.github_oidc}"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 0 : 1

  url = "https://${local.github_oidc}"
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    sid     = "GitHubActionsOnMainOnly"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc}:sub"
      values   = ["repo:${var.github_repo}:ref:${var.github_ref}"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "gigawhat-github-deploy"
  description          = "GitHub Actions (${var.github_repo} on ${var.github_ref}) redeploys GigaWhat via Run Command"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "deploy" {
  # SendCommand is authorised against both the document and each target instance.
  statement {
    sid     = "RunShellScriptDocumentOnly"
    actions = ["ssm:SendCommand"]
    # AWS-owned documents have no account in their ARN; customers can't create AWS-* documents.
    resources = ["arn:${local.partition}:ssm:${var.region}:*:document/AWS-RunShellScript"]
  }

  statement {
    sid       = "OnGigaWhatInstancesOnly"
    actions   = ["ssm:SendCommand"]
    resources = [local.instance_arn]

    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/Project"
      values   = [var.project_tag]
    }
  }

  # Neither action supports resource-level permissions.
  statement {
    sid = "FollowTheDeployment"
    actions = [
      "ssm:GetCommandInvocation",
      "ec2:DescribeInstances",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "gigawhat-deploy"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}
