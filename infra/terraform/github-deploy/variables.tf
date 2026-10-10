variable "region" {
  description = "The project's AWS Region, where the GigaWhat instance runs."
  type        = string
  default     = "eu-north-1"
}

variable "github_repo" {
  description = "owner/name of the only repository allowed to assume the deploy role. Must match GitHub's casing."
  type        = string
  default     = "vishalsmak/gigawhat"
}

variable "github_ref" {
  description = "The only Git ref allowed to deploy."
  type        = string
  default     = "refs/heads/main"
}

variable "project_tag" {
  description = "Value of the Project tag on the instances the role may run commands on."
  type        = string
  default     = "gigawhat"
}

variable "create_oidc_provider" {
  description = "Set to false if this AWS account already has a token.actions.githubusercontent.com provider."
  type        = bool
  default     = true
}
