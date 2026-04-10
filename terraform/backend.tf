# Bootstrap (one-time, run manually before `terraform init`):
#
#   gcloud auth application-default login
#   gcloud config set project carnegie-roi-reports
#   gcloud services enable storage.googleapis.com --project carnegie-roi-reports
#   gsutil mb -p carnegie-roi-reports -l us-east4 gs://carnegie-roi-reports-tfstate
#   gsutil versioning set on gs://carnegie-roi-reports-tfstate

terraform {
  backend "gcs" {
    bucket = "carnegie-roi-reports-tfstate"
    # prefix is set at init time via -backend-config:
    #   prod: roi-report/terraform/state/prod
    #   dev:  roi-report/terraform/state/dev
  }
}
