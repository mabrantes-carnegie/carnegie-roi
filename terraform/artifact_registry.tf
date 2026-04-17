resource "google_artifact_registry_repository" "app" {
  repository_id = local.repo_name
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for ROI Reports app (${var.environment})"
}
