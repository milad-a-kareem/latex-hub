from datetime import timedelta

from ..firebase import bucket


def upload_pdf(project_id: str, pdf: bytes) -> str:
    blob = bucket().blob(f"projects/{project_id}/build/output.pdf")
    blob.upload_from_string(pdf, content_type="application/pdf")
    return blob.generate_signed_url(expiration=timedelta(minutes=30), method="GET")
