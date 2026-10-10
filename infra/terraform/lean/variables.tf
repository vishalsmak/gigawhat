variable "region" {
  description = "The project's AWS Region. New-experience projects can only create resources here."
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "Graviton (arm64) instance type. t4g.small has 2 vCPUs and 2 GiB of memory."
  type        = string
  default     = "t4g.small"

  validation {
    condition     = can(regex("^[a-z]+[0-9]+[a-z]*g[a-z]*\\.", var.instance_type))
    error_message = "Use a Graviton (arm64) instance type such as t4g.small: the AMI is arm64."
  }
}

variable "cpu_credits" {
  description = <<-EOT
    Burstable CPU credit mode. "standard" throttles to the baseline when credits run out and never
    bills extra; "unlimited" (the AWS default for t4g) keeps bursting and bills surplus credits.
  EOT
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["standard", "unlimited"], var.cpu_credits)
    error_message = "cpu_credits must be \"standard\" or \"unlimited\"."
  }
}

variable "root_volume_size_gb" {
  description = "Size of the encrypted gp3 root volume. It holds Docker images and the Postgres data."
  type        = number
  default     = 20
}

variable "github_repo" {
  description = "GitHub repository (owner/name) that holds the deploy/ files the instance downloads."
  type        = string
  default     = "vishalsmak/gigawhat"
}

variable "git_ref" {
  description = "Branch, tag or commit to download the deploy/ files from."
  type        = string
  default     = "main"
}

variable "compose_version" {
  description = "Docker Compose plugin release to install (github.com/docker/compose/releases)."
  type        = string
  default     = "v5.6.0"
}

variable "snapshot_retain_count" {
  description = "How many daily snapshots of the root volume to keep."
  type        = number
  default     = 7
}

variable "seed_expiry_days" {
  description = "Days after which objects in the seed bucket are deleted."
  type        = number
  default     = 30
}
