#!/usr/bin/env bash
# Build and deploy the backend image to Cloud Run.
#
# Usage: PROJECT_ID=my-proj REGION=us-central1 infra/cloudrun/deploy.sh
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-latex-hub-api}"
REPO="${REPO:-latex-hub}"
# Default to the new <project>.firebasestorage.app naming used by Firebase
# projects created after Oct 2024. Override for older projects.
BUCKET="${FIREBASE_STORAGE_BUCKET:-${PROJECT_ID}.firebasestorage.app}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:$(date +%Y%m%d-%H%M%S)"

gcloud builds submit backend \
  --tag "${IMAGE}" \
  --project "${PROJECT_ID}"

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "FIREBASE_PROJECT_ID=${PROJECT_ID},FIREBASE_STORAGE_BUCKET=${BUCKET}" \
  --cpu 2 --memory 2Gi --concurrency 40 --timeout 300 \
  --session-affinity
