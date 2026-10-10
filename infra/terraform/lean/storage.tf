# Private bucket for the database seed dump. The instance reads it once when the database is seeded.

resource "aws_s3_bucket" "seed" {
  bucket = "gigawhat-seed-${local.account_id}"

  # It only ever holds a dump you can recreate locally, so `terraform destroy` empties it too.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "seed" {
  bucket = aws_s3_bucket.seed.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "seed" {
  bucket = aws_s3_bucket.seed.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "seed" {
  bucket = aws_s3_bucket.seed.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "seed" {
  bucket = aws_s3_bucket.seed.id

  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "seed" {
  bucket = aws_s3_bucket.seed.id

  rule {
    id     = "expire-seed-dumps"
    status = "Enabled"

    filter {}

    expiration {
      days = var.seed_expiry_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

data "aws_iam_policy_document" "seed_bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.seed.arn, "${aws_s3_bucket.seed.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "seed" {
  bucket = aws_s3_bucket.seed.id
  policy = data.aws_iam_policy_document.seed_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.seed]
}
