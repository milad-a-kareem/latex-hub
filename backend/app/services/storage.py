"""Cloud Storage upload helpers.

On Cloud Run we authenticate via ADC (no private key in the environment),
so ``blob.generate_signed_url`` cannot sign with a local key. Instead we
ask the IAM Credentials API to sign on our behalf via the runtime SA. The
runtime SA must hold ``roles/iam.serviceAccountTokenCreator`` on itself.
"""

import contextlib
from datetime import timedelta
from typing import cast

import google.auth
from google.auth.transport.requests import Request

from ..firebase import bucket


def _signed_get_url(blob_path: str, minutes: int = 30) -> str:
    blob = bucket().blob(blob_path)
    credentials, _ = google.auth.default()
    credentials.refresh(Request())  # type: ignore[no-untyped-call]
    sa_email = getattr(credentials, "service_account_email", None)
    return cast(
        str,
        blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="GET",
            service_account_email=sa_email,
            access_token=credentials.token,
        ),
    )


def upload_pdf(project_id: str, pdf: bytes) -> str:
    blob = bucket().blob(f"projects/{project_id}/build/output.pdf")
    blob.upload_from_string(pdf, content_type="application/pdf")
    return _signed_get_url(blob.name)


def upload_asset(project_id: str, path: str, data: bytes, content_type: str) -> None:
    blob = bucket().blob(f"projects/{project_id}/assets/{path}")
    blob.upload_from_string(data, content_type=content_type or "application/octet-stream")


def signed_asset_url(project_id: str, path: str) -> str:
    return _signed_get_url(f"projects/{project_id}/assets/{path}")


def download_asset_bytes(project_id: str, path: str) -> bytes:
    blob = bucket().blob(f"projects/{project_id}/assets/{path}")
    return cast(bytes, blob.download_as_bytes())


def delete_asset(project_id: str, path: str) -> None:
    blob = bucket().blob(f"projects/{project_id}/assets/{path}")
    with contextlib.suppress(Exception):
        blob.delete()


def delete_project_prefix(project_id: str) -> None:
    prefix = f"projects/{project_id}/"
    for blob in bucket().list_blobs(prefix=prefix):
        with contextlib.suppress(Exception):
            blob.delete()
