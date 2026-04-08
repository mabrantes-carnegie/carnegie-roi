resource "google_cloud_run_v2_service" "app" {
  name     = "roi-reports"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/roi-reports/roi-reports-app:${var.image_tag}"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
  }

  depends_on = [google_artifact_registry_repository.app]
}
