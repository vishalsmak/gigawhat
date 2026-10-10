output "role_arn" {
  description = "Set as role-to-assume in aws-actions/configure-aws-credentials."
  value       = aws_iam_role.deploy.arn
}
