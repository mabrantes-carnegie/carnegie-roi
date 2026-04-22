resource "google_service_account" "cloud_run_sa" {
  account_id   = "roi-reports-run-${var.environment}"
  display_name = "ROI Reports Cloud Run (${var.environment})"
}

# Allow the Cloud Run SA to run BigQuery jobs billed to this project.
# Read access to source datasets (unified-data-platform-prod, carnegie-dartlet)
# is granted out-of-band on those projects.
resource "google_project_iam_member" "cloud_run_sa_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Required for BigQuery Storage API (faster to_dataframe via gRPC).
resource "google_project_iam_member" "cloud_run_sa_bq_read_session" {
  project = var.project_id
  role    = "roles/bigquery.readSessionUser"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
