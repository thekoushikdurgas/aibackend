"""Non-secret cloud integration status (env-based)."""

import os

from fastapi import APIRouter

router = APIRouter(tags=["integrations"])


@router.get("/integrations/cloud")
def cloud_env_status() -> dict:
    """
    Return which integration env vars are set (no secret values are exposed).
    Adapters and credentials must stay on the server.
    """
    return {
        "s3Compatible": {
            "endpoint": bool(os.environ.get("VSQL_S3_ENDPOINT")),
            "bucket": bool(os.environ.get("VSQL_S3_BUCKET")),
            "region": bool(os.environ.get("VSQL_S3_REGION")),
        },
        "azure": {
            "account": bool(os.environ.get("VSQL_AZURE_ACCOUNT")),
        },
        "gcs": {
            "bucket": bool(os.environ.get("VSQL_GCS_BUCKET")),
        },
        "note": "Store access keys only in environment variables or a secret vault, never in vSQL video frames.",
    }
