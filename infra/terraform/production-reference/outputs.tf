output "load_balancer_dns_name" {
  description = "Point the public hostname (CNAME or Route 53 alias) here."
  value       = aws_lb.app.dns_name
}

output "database_endpoint" {
  description = "RDS endpoint, reachable only from the app tasks."
  value       = aws_db_instance.main.endpoint
}

output "database_secret_arn" {
  description = "Secrets Manager secret holding the RDS-managed master password."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "app_secret_arn" {
  description = "Set its value with aws secretsmanager put-secret-value (see the comment in data.tf)."
  value       = aws_secretsmanager_secret.app.arn
}

output "web_acl_arn" {
  description = "WAF web ACL attached to the load balancer."
  value       = aws_wafv2_web_acl.app.arn
}

output "log_group" {
  description = "CloudWatch log group for the app containers."
  value       = aws_cloudwatch_log_group.app.name
}
