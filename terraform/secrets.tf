resource "google_secret_manager_secret" "jwt_secret" {
  secret_id  = "roi-reports-jwt-secret-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "cookie_secret" {
  secret_id  = "roi-reports-cookie-secret-${var.environment}"
  replication {
    auto {}
  }
}

# Grant the Cloud Run SA read access to both secrets
resource "google_secret_manager_secret_iam_member" "jwt_secret_access" {
  secret_id = google_secret_manager_secret.jwt_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cookie_secret_access" {
  secret_id = google_secret_manager_secret.cookie_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ──────────────────────────────────────────────────────────────
# One-time bootstrap: add secret values manually (never in TF).
# Run once per environment after `terraform apply`:
#
#   openssl rand -base64 32 | \
#     gcloud secrets versions add roi-reports-jwt-secret-<ENV> \
#       --data-file=- --project=carnegie-roi-reports
#
#   openssl rand -base64 32 | \
#     gcloud secrets versions add roi-reports-cookie-secret-<ENV> \
#       --data-file=- --project=carnegie-roi-reports
# ──────────────────────────────────────────────────────────────
