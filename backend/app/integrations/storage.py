"""Object storage (S3 / MinIO) for media uploads (docs/11 §3, docs/12).

Local dev uploads to MinIO (settings.s3_endpoint_url). The avatars bucket is made
public-read so the browser can load images by direct URL; in prod this would be a
private bucket served via signed CloudFront URLs.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import anyio
import boto3

from app.core.config import settings

_PUBLIC_READ_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{settings.s3_bucket}/*",
        }
    ],
}


@lru_cache(maxsize=1)
def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.aws_region,
    )


def _ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)
    try:  # idempotent; safe to re-apply each upload
        client.put_bucket_policy(Bucket=settings.s3_bucket, Policy=json.dumps(_PUBLIC_READ_POLICY))
    except Exception:
        pass


def _put_object(data: bytes, key: str, content_type: str) -> str:
    _ensure_bucket()
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)
    base = (settings.s3_public_base_url or settings.s3_endpoint_url or "").rstrip("/")
    return f"{base}/{settings.s3_bucket}/{key}"


async def upload_bytes(data: bytes, key: str, content_type: str) -> str:
    """Upload bytes and return the public URL. Runs the blocking boto3 call off the loop."""
    return await anyio.to_thread.run_sync(_put_object, data, key, content_type)
