data "google_project" "current" {
  project_id = var.project_id
}

resource "google_cloud_run_v2_service" "app" {
  name        = var.service_name
  location    = var.region
  ingress     = "INGRESS_TRAFFIC_ALL"
  iap_enabled = true

  template {
    containers {
      image = local.image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = var.memory
          cpu    = var.cpu
        }
      }
    }

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
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

# IAP domain access for @carnegiehighered.com — applied via gcloud (one-time per service)
# due to provider bug in hashicorp/google (tested on 7.26 and 7.27):
#
#   # prod
#   gcloud iap web add-iam-policy-binding \
#     --resource-type=cloud-run \
#     --service=roi-reports \
#     --region=us-east4 \
#     --member="domain:carnegiehighered.com" \
#     --role="roles/iap.httpsResourceAccessor" \
#     --project=carnegie-roi-reports
#
#   # dev
#   gcloud iap web add-iam-policy-binding \
#     --resource-type=cloud-run \
#     --service=roi-reports-dev \
#     --region=us-east4 \
#     --member="domain:carnegiehighered.com" \
#     --role="roles/iap.httpsResourceAccessor" \
#     --project=carnegie-roi-reports
