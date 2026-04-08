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

variable "github_repo" {
  description = "GitHub repo (org/name) allowed to authenticate via WIF"
  type        = string
  default     = "CarnegieHigherEd/roi-report"
}

variable "invoker_members" {
  description = "List of IAM members allowed to invoke the Cloud Run service (e.g. user:x@y.com, group:team@y.com, serviceAccount:sa@project.iam.gserviceaccount.com)"
  type        = list(string)
  default     = []
}
