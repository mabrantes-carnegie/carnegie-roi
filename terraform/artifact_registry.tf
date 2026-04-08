resource "google_artifact_registry_repository" "app" {
  repository_id = "roi-reports"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for ROI Reports app"


}
