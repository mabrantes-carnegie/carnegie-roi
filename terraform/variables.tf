variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "carnegie-roi-reports"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-east4"
}

variable "image_tag" {
  description = "Docker image tag to deploy (typically the Git SHA)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev or prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be 'dev' or 'prod'"
  }
}

locals {
  service_name = var.environment == "prod" ? "roi-reports" : "roi-reports-${var.environment}"
  repo_name    = var.environment == "prod" ? "roi-reports" : "roi-reports-${var.environment}"
  image        = "${var.region}-docker.pkg.dev/${var.project_id}/${local.repo_name}/roi-reports-app:${var.image_tag}"
}

variable "github_repo" {
  description = "GitHub repo (org/name) allowed to authenticate via WIF"
  type        = string
  default     = "CarnegieHigherEd/roi-report"
}


