resource "google_service_account" "cloud_run_sa" {
  account_id   = "roi-reports-run-${var.environment}"
  display_name = "ROI Reports Cloud Run (${var.environment})"
}
