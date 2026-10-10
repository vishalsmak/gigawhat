output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.app.public_ip
}

output "hostname" {
  description = "Free HTTPS hostname. sslip.io resolves it to the Elastic IP; Caddy gets the certificate."
  value       = local.hostname
}

output "url" {
  description = "Where the app is served once the bootstrap has finished."
  value       = "https://${local.hostname}"
}

output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.app.id
}

output "seed_bucket" {
  description = "Private S3 bucket for the database seed dump."
  value       = aws_s3_bucket.seed.bucket
}

output "ssm_connect_command" {
  description = "Opens a shell on the instance through Session Manager (needs the Session Manager plugin)."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.app.id}"
}
