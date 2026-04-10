# One-time project bootstrap: see scripts/bootstrap.sh

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
