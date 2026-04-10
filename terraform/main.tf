# Bootstrap (one-time, run manually before `terraform init`):
#
#   gcloud auth application-default login
#   gcloud config set project carnegie-roi-reports
#   gcloud services enable storage.googleapis.com --project carnegie-roi-reports
#   gsutil mb -p carnegie-roi-reports -l us-east4 gs://carnegie-roi-reports-tfstate
#   gsutil versioning set on gs://carnegie-roi-reports-tfstate

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.26.0"
    }
  }

  backend "gcs" {
    bucket = "carnegie-roi-reports-tfstate"
    # prefix is set at init time via -backend-config:
    #   prod: roi-report/terraform/state/prod
    #   dev:  roi-report/terraform/state/dev
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name = "roi-reports-${var.environment}"
  repo_name    = "roi-reports-${var.environment}"
  image        = "${var.region}-docker.pkg.dev/${var.project_id}/${local.repo_name}/roi-reports-app:${var.image_tag}"
}
