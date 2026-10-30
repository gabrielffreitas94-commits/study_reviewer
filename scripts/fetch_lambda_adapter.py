"""Utility script to ensure the AWS Lambda Web Adapter binary is present in bin/lambda-adapter.

This prevents Docker builds from failing due to anonymous rate-limiting (HTTP 429)
on public.ecr.aws in CI/CD runner environments.
"""

from __future__ import annotations

import io
import json
import os
import stat
import tarfile
import urllib.request

ADAPTER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin", "lambda-adapter")
AMD64_BLOB_DIGEST = "sha256:e98b5f6c982bfcd4224894093919fa40f249ce5fa5ea9d328b7859318bcb2616"


def ensure_lambda_adapter() -> None:
    if os.path.exists(ADAPTER_PATH) and os.path.getsize(ADAPTER_PATH) > 1_000_000:
        size = os.path.getsize(ADAPTER_PATH)
        print(f"[OK] Lambda adapter binary already present at {ADAPTER_PATH} ({size} bytes)")
        return

    dest_dir = os.path.dirname(ADAPTER_PATH)
    os.makedirs(dest_dir, exist_ok=True)
    print("==> Fetching Lambda adapter binary from ECR Public with bearer token...")

    with urllib.request.urlopen("https://public.ecr.aws/token/") as token_res:  # noqa: S310
        token = json.loads(token_res.read())["token"]

    blob_url = f"https://public.ecr.aws/v2/awsguru/aws-lambda-adapter/blobs/{AMD64_BLOB_DIGEST}"
    blob_req = urllib.request.Request(blob_url, headers={"Authorization": f"Bearer {token}"})

    with urllib.request.urlopen(blob_req) as response:  # noqa: S310
        layer_bytes = response.read()

    with tarfile.open(fileobj=io.BytesIO(layer_bytes), mode="r:*") as tar:
        tar.extractall(path=dest_dir, filter="data")  # noqa: S202

    current_mode = os.stat(ADAPTER_PATH).st_mode
    os.chmod(ADAPTER_PATH, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)  # noqa: S103
    size = os.path.getsize(ADAPTER_PATH)
    print(f"[OK] Successfully extracted lambda-adapter to {ADAPTER_PATH} ({size} bytes)")


if __name__ == "__main__":
    ensure_lambda_adapter()
