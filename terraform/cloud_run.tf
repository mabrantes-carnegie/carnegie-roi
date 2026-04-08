data "google_project" "current" {
  project_id = var.project_id
}

resource "google_cloud_run_v2_service" "app" {
  name        = "roi-reports"
  location    = var.region
  ingress     = "INGRESS_TRAFFIC_ALL"
  iap_enabled = true

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

# Grant the IAP service agent invoker access so it can forward
# authenticated requests to Cloud Run on behalf of users.
resource "google_cloud_run_v2_service_iam_member" "iap_sa_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# Grant the entire @carnegiehighered.com domain access through IAP.
resource "google_iap_web_cloud_run_service_iam_member" "domain_access" {
  project                = var.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.app.name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "domain:carnegiehighered.com"
}
