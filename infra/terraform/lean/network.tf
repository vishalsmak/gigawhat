# The default VPC keeps this cheap and simple: public subnets with an internet gateway, so no NAT
# gateway or load balancer is needed. Caddy on the instance terminates HTTPS itself.

data "aws_vpc" "default" {
  default = true
}

# Only consider Availability Zones that actually offer the chosen instance type.
data "aws_ec2_instance_type_offerings" "app" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.instance_type]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }

  filter {
    name   = "availability-zone"
    values = data.aws_ec2_instance_type_offerings.app.locations
  }
}

locals {
  subnet_id = length(data.aws_subnets.default.ids) > 0 ? sort(data.aws_subnets.default.ids)[0] : null
}

resource "aws_security_group" "app" {
  name        = "gigawhat-web"
  description = "GigaWhat: HTTP and HTTPS in, everything out. No SSH: use Session Manager."
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "gigawhat-web"
  }
}

locals {
  # Port 80 stays open so Caddy can answer the Let's Encrypt HTTP-01 challenge and redirect to HTTPS.
  web_ingress = {
    http_ipv4  = { port = 80, cidr_ipv4 = "0.0.0.0/0", cidr_ipv6 = null }
    http_ipv6  = { port = 80, cidr_ipv4 = null, cidr_ipv6 = "::/0" }
    https_ipv4 = { port = 443, cidr_ipv4 = "0.0.0.0/0", cidr_ipv6 = null }
    https_ipv6 = { port = 443, cidr_ipv4 = null, cidr_ipv6 = "::/0" }
  }
}

resource "aws_vpc_security_group_ingress_rule" "web" {
  for_each = local.web_ingress

  security_group_id = aws_security_group.app.id
  description       = "Public web traffic (${each.key})"
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  cidr_ipv4         = each.value.cidr_ipv4
  cidr_ipv6         = each.value.cidr_ipv6
}

resource "aws_vpc_security_group_egress_rule" "all_ipv4" {
  security_group_id = aws_security_group.app.id
  description       = "All outbound IPv4: package installs, GHCR, Anthropic, Cohere, AWS APIs"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "all_ipv6" {
  security_group_id = aws_security_group.app.id
  description       = "All outbound IPv6"
  ip_protocol       = "-1"
  cidr_ipv6         = "::/0"
}
