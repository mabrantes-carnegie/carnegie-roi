#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# One-time GCP project bootstrap
# Run once per project, not per environment.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_ID="carnegie-roi-reports"
REGION="us-east4"
GITHUB_REPO="CarnegieHigherEd/roi-report"

echo "── Setting project ──"
gcloud config set project "$PROJECT_ID"

# ── APIs ──
echo "── Enabling APIs ──"
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iap.googleapis.com \
  iam.googleapis.com \
  sts.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID"

# ── Terraform state bucket ──
echo "── Creating Terraform state bucket ──"
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${PROJECT_ID}-tfstate" 2>/dev/null || echo "Bucket already exists"
gsutil versioning set on "gs://${PROJECT_ID}-tfstate"

# ── Service Account for GitHub Actions ──
echo "── Creating service account ──"
gcloud iam service-accounts create github-actions-deploy \
  --display-name="GitHub Actions Deploy" \
  --description="Used by GitHub Actions via Workload Identity Federation" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Service account already exists"

SA_EMAIL="github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant owner role (needed for Terraform apply)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/owner" \
  --condition=None

# ── Workload Identity Federation ──
echo "── Creating WIF pool ──"
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --description="Pool for GitHub Actions OIDC tokens" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Pool already exists"

echo "── Creating WIF OIDC provider ──"
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub OIDC" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Provider already exists"

echo "── Binding WIF to service account ──"
POOL_NAME=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global --project="$PROJECT_ID" --format="value(name)")

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}" \
  --project="$PROJECT_ID"

# ── IAP domain bindings (run once per Cloud Run service) ──
echo "── IAP domain bindings ──"
for ENV in dev prod; do
  echo "  Binding IAP for roi-reports-${ENV}..."
  gcloud iap web add-iam-policy-binding \
    --resource-type=cloud-run \
    --service="roi-reports-${ENV}" \
    --region="$REGION" \
    --member="domain:carnegiehighered.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || echo "  Service roi-reports-${ENV} not deployed yet — run after first deploy"
done

# ── Print values for GitHub secrets ──
echo ""
echo "══════════════════════════════════════════════"
echo "  Add these as GitHub Actions secrets:"
echo "══════════════════════════════════════════════"

WIF_PROVIDER=$(gcloud iam workload-identity-pools providers describe github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --project="$PROJECT_ID" \
  --format="value(name)")

echo "  WIF_PROVIDER:        ${WIF_PROVIDER}"
echo "  WIF_SERVICE_ACCOUNT: ${SA_EMAIL}"
echo "══════════════════════════════════════════════"
