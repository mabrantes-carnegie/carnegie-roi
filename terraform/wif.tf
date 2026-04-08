# ──────────────────────────────────────────────
# Workload Identity Federation for GitHub Actions
# ──────────────────────────────────────────────

# 1. Service Account that GitHub Actions will impersonate
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deploy"
  display_name = "GitHub Actions Deploy"
  description  = "Used by GitHub Actions via Workload Identity Federation"

}

# 2. Workload Identity Pool
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Pool for GitHub Actions OIDC tokens"
}

# 3. OIDC Provider (GitHub)
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 4. Allow the GitHub pool to impersonate the service account
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# 5. SA permissions are granted via roles/owner (applied manually via gcloud cli).

# ──────────────────────────────────────────────
# Outputs needed for GitHub Actions workflow
# ──────────────────────────────────────────────

output "wif_provider" {
  description = "Full provider resource name for GitHub Actions auth"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "wif_service_account" {
  description = "Service account email for GitHub Actions"
  value       = google_service_account.github_actions.email
}
