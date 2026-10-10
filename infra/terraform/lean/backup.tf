# Daily snapshots of the root volume, which holds the Postgres data. Snapshots are incremental and
# crash-consistent; Postgres recovers from them as it would after a power cut.

resource "aws_dlm_lifecycle_policy" "root_volume" {
  description        = "GigaWhat daily root volume snapshots"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    target_tags = {
      SnapshotPolicy = "gigawhat-daily"
    }

    schedule {
      name      = "daily"
      copy_tags = true

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"] # UTC
      }

      retain_rule {
        count = var.snapshot_retain_count
      }

      tags_to_add = {
        SnapshotCreator = "dlm"
      }
    }
  }

  tags = {
    Name = "gigawhat-daily-snapshots"
  }
}
