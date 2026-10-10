variable "region" {
  description = "The project's AWS Region. Everything, including WAF and the certificate, lives here."
  type        = string
  default     = "eu-north-1"
}

variable "name" {
  description = "Name prefix for every resource."
  type        = string
  default     = "gigawhat"
}

variable "vpc_cidr" {
  description = "VPC address range. Subnets are /24s carved from it."
  type        = string
  default     = "10.20.0.0/16"
}

variable "certificate_arn" {
  description = "ACM certificate for the public hostname, issued in the same Region as the load balancer."
  type        = string
}

variable "container_image" {
  description = "App image, ideally in ECR with image scanning and pinned by digest."
  type        = string
}

variable "container_port" {
  description = "Port uvicorn listens on inside the container."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of app tasks. Two or more spreads them across both Availability Zones."
  type        = number
  default     = 2
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 2048
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.m7g.large"
}

variable "db_allocated_storage_gb" {
  description = "Initial database storage. Storage autoscaling grows it up to db_max_allocated_storage_gb."
  type        = number
  default     = 50
}

variable "db_max_allocated_storage_gb" {
  description = "Upper limit for storage autoscaling."
  type        = number
  default     = 200
}

variable "db_backup_retention_days" {
  description = "Automated backup retention, which also sets the point-in-time recovery window."
  type        = number
  default     = 14
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for app, database and VPC flow logs."
  type        = number
  default     = 90
}

variable "waf_rate_limit" {
  description = "Requests per IP address in any 5-minute window before WAF blocks that address."
  type        = number
  default     = 500
}

variable "bedrock_model_pattern" {
  description = "Bedrock foundation-model IDs the app may invoke."
  type        = string
  default     = "anthropic.claude-*"
}
