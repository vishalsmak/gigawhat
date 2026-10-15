# The hosted demo: one small arm64 server running Docker Compose, behind CloudFront for HTTPS.
# Secrets live in Parameter Store (put there by put_secrets.py), never in this state.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Fixed rather than variables: put_secrets.py and copy_data.sh use the same two values.
locals {
  region  = "eu-north-1"
  profile = "gigawhat"
}

provider "aws" {
  region  = local.region
  profile = local.profile
  default_tags {
    tags = { Project = "gigawhat" }
  }
}

data "aws_caller_identity" "current" {}

data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

# The server's identity: Systems Manager access (instead of SSH) and the app's parameters.
resource "aws_iam_role" "app" {
  name = "gigawhat-app"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "systems_manager" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "parameters" {
  name = "read-gigawhat-parameters"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ssm:GetParametersByPath"
      Resource = "arn:aws:ssm:${local.region}:${data.aws_caller_identity.current.account_id}:parameter/gigawhat"
    }]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "gigawhat-app"
  role = aws_iam_role.app.name
}

resource "aws_security_group" "app" {
  name        = "gigawhat-app"
  description = "HTTP from CloudFront only. No SSH: use Systems Manager."
}

resource "aws_vpc_security_group_ingress_rule" "cloudfront" {
  security_group_id = aws_security_group.app.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.ubuntu.insecure_value
  instance_type          = "t4g.small"
  iam_instance_profile   = aws_iam_instance_profile.app.name
  vpc_security_group_ids = [aws_security_group.app.id]
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    compose = filebase64("${path.module}/compose.yaml")
    deploy  = filebase64("${path.module}/deploy.sh")
  })

  metadata_options {
    http_tokens = "required"
  }

  # Standard credits throttle the CPU when they run out, instead of billing for more.
  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = { Name = "gigawhat" }

  # The first boot reads the parameters, so the policy must exist before the server starts.
  depends_on = [aws_iam_role_policy.parameters]

  lifecycle {
    # The database lives on this disk, so a newer Ubuntu image or an edited first-boot file
    # must never replace the server.
    ignore_changes = [ami, user_data]
  }
}

# A fixed address keeps CloudFront's origin valid if the server is stopped and started.
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  tags     = { Name = "gigawhat" }
}

resource "aws_cloudfront_distribution" "app" {
  enabled      = true
  comment      = "GigaWhat demo"
  price_class  = "PriceClass_100"
  http_version = "http2and3"

  origin {
    origin_id   = "app"
    domain_name = aws_eip.app.public_dns

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
    }
  }

  default_cache_behavior {
    target_origin_id         = "app"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
    compress                 = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
