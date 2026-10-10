terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Local state, as for the lean module. A team would use an S3 backend with use_lockfile = true.
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "gigawhat"
      ManagedBy = "terraform"
    }
  }
}
