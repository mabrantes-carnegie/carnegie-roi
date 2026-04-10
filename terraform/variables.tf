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
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "environment" {
  description = "Deployment environment (dev or prod)"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be 'dev' or 'prod'"
  }
}

variable "min_instances" {
  description = "Minimum Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 1
}

variable "cpu" {
  description = "Cloud Run CPU limit"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Cloud Run memory limit"
  type        = string
  default     = "512Mi"
}

variable "github_repo" {
  description = "GitHub repo (org/name) allowed to authenticate via WIF"
  type        = string
  default     = "CarnegieHigherEd/roi-report"
}
