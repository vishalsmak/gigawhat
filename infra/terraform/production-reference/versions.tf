# REFERENCE ONLY: validated with `terraform validate`, never planned or applied. It shows what a
# regulated company would run instead of the lean EC2 instance, and costs an order of magnitude more.

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.28"
    }
  }

  # A real deployment would use an S3 backend with locking (use_lockfile = true) in the project Region.
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.name
      ManagedBy = "terraform"
    }
  }
}
