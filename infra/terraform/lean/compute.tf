# Latest Amazon Linux 2023 arm64 AMI. Read once at creation: see ignore_changes below.
data "aws_ssm_parameter" "al2023_arm64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

# The Elastic IP is created before the instance so its address (and so the sslip.io hostname) can
# be passed to the bootstrap script without a dependency cycle.
resource "aws_eip" "app" {
  domain = "vpc"

  tags = {
    Name = "gigawhat"
  }
}

locals {
  hostname = "gigawhat-${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_arm64.insecure_value
  instance_type          = var.instance_type
  subnet_id              = local.subnet_id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.instance.name
  monitoring             = false # detailed (1-minute) monitoring costs extra; 5-minute is enough here

  # No key pair and no port 22: administration is through Session Manager only.

  credit_specification {
    cpu_credits = var.cpu_credits
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 only
    # Hop limit 1 means containers on the Docker bridge can't reach the metadata service, so a
    # compromised container can't take the instance role's credentials. Only the host scripts use
    # AWS. Raise to 2 if a container ever needs AWS credentials.
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name           = "gigawhat-root"
      SnapshotPolicy = "gigawhat-daily"
    }
  }

  # Holds no secrets: the instance reads them from Parameter Store at runtime.
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region          = var.region
    github_repo     = var.github_repo
    git_ref         = var.git_ref
    compose_version = var.compose_version
    public_ip       = aws_eip.app.public_ip
    default_domain  = local.hostname
  })

  tags = {
    Name = "gigawhat"
  }

  lifecycle {
    # A new AMI or bootstrap script would otherwise replace or restart the instance and, with it,
    # the Postgres data on the root volume. Use `terraform apply -replace=aws_instance.app` when
    # you really want a fresh instance.
    ignore_changes = [ami, user_data]

    precondition {
      condition     = local.subnet_id != null
      error_message = "No default subnet offers ${var.instance_type}. Recreate the default VPC (aws ec2 create-default-vpc) or pick another instance type."
    }
  }
}

resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}
