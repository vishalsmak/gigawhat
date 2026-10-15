output "url" {
  description = "The link to share."
  value       = "https://${aws_cloudfront_distribution.app.domain_name}"
}

output "instance_id" {
  description = "For Systems Manager sessions and commands."
  value       = aws_instance.app.id
}
