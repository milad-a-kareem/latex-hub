"""Cloud Storage upload helpers.

On Cloud Run we authenticate via ADC (no private key in the environment),
so ``blob.generate_signed_url`` cannot sign with a local key. Instead we
ask the IAM Credentials API to sign on our behalf via the runtime SA. The
runtime SA must hold ``roles/iam.serviceAccountTokenCreator`` on itself.
"""

from datetime import timedelta
from typing import cast

import google.auth
from google.auth.transport.requests import Request

from ..firebase import bucket


def upload_pdf(project_id: str, pdf: bytes) -> str:
    blob = bucket().blob(f"projects/{project_id}/build/output.pdf")
    blob.upload_from_string(pdf, content_type="application/pdf")

    credentials, _ = google.auth.default()
    credentials.refresh(Request())  # type: ignore[no-untyped-call]
    sa_email = getattr(credentials, "service_account_email", None)

    return cast(
        str,
        blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=30),
            method="GET",
            service_account_email=sa_email,
            access_token=credentials.token,
        ),
    )
