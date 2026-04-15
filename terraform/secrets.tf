resource "google_secret_manager_secret" "jwt_public_key" {
  secret_id = "roi-reports-jwt-public-key-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "jwt_private_key" {
  secret_id = "roi-reports-jwt-private-key-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "cookie_secret" {
  secret_id = "roi-reports-cookie-secret-${var.environment}"
  replication {
    auto {}
  }
}

# Grant the Cloud Run SA read access to secrets it needs at runtime
resource "google_secret_manager_secret_iam_member" "jwt_public_key_access" {
  secret_id = google_secret_manager_secret.jwt_public_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "cookie_secret_access" {
  secret_id = google_secret_manager_secret.cookie_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
