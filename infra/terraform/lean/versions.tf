terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is kept locally (terraform.tfstate, git-ignored). That is fine for one person running a
  # demo. A team would keep it in S3 with locking so two applies can't race, for example:
  #
  # backend "s3" {
  #   bucket       = "gigawhat-tfstate-<account_id>"
  #   key          = "lean/terraform.tfstate"
  #   region       = "eu-north-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
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
