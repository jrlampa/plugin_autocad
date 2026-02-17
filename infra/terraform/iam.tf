# Service Account for sisRUA
resource "google_service_account" "sisrua_sa" {
  account_id   = "sisrua-production-sa"
  display_name = "sisRUA Production Service Account"
}

# Locked IAM roles for the service account
resource "google_project_iam_member" "logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.sisrua_sa.email}"
}

resource "google_project_iam_member" "monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.sisrua_sa.email}"
}
