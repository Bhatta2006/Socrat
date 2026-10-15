import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

from socrat.foundry.compliance import PolicyBlocked


def object_key(source_id: str, body: bytes) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,36}", source_id):
        raise PolicyBlocked("invalid_object_key")
    return f"sources/{source_id}/{hashlib.sha256(body).hexdigest()}"


class SnapshotStore(Protocol):
    def put(self, key: str, body: bytes, context) -> None: ...
    def get(self, key: str, context) -> bytes: ...
    def delete(self, key: str, context) -> None: ...


class LocalStore:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def path(self, key):
        if not re.fullmatch(r"sources/[a-zA-Z0-9-]{1,36}/[a-f0-9]{64}", key):
            raise PolicyBlocked("invalid_object_key")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise PolicyBlocked("invalid_object_key")
        return path

    def put(self, key: str, body: bytes, context):
        context.reserve()
        if len(body) > context.settings.max_bytes or key != object_key(key.split("/")[1], body):
            raise PolicyBlocked("invalid_snapshot")
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temp = Path(handle.name)
                handle.write(body)
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def get(self, key: str, context) -> bytes:
        context.reserve()
        with self.path(key).open("rb") as handle:
            body = handle.read(context.settings.max_bytes + 1)
        if len(body) > context.settings.max_bytes or key != object_key(key.split("/")[1], body):
            raise PolicyBlocked("invalid_snapshot")
        return body

    def delete(self, key: str, context):
        context.reserve()
        self.path(key).unlink(missing_ok=True)


class S3Store:
    def __init__(self, bucket: str, endpoint: str = "", client=None, *, live=True):
        self.bucket, self.endpoint, self.client = bucket, endpoint, client
        self.live = live

    def sdk(self, context):
        context.reserve(live=self.live)
        if self.client is not None:
            return self.client
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint or None,
            config=Config(
                connect_timeout=min(10, context.remaining_seconds()),
                read_timeout=min(20, context.remaining_seconds()),
                retries={"total_max_attempts": 1},
            ),
        )

    def put(self, key: str, body: bytes, context):
        if len(body) > context.settings.max_bytes or key != object_key(key.split("/")[1], body):
            raise PolicyBlocked("invalid_snapshot")
        self.sdk(context).put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ServerSideEncryption="AES256",
            Metadata={"sha256": key.split("/")[-1]},
        )

    def get(self, key: str, context) -> bytes:
        stream = self.sdk(context).get_object(Bucket=self.bucket, Key=key)["Body"]
        try:
            body = stream.read(context.settings.max_bytes + 1)
        finally:
            stream.close()
        if len(body) > context.settings.max_bytes or key != object_key(key.split("/")[1], body):
            raise PolicyBlocked("invalid_snapshot")
        return body

    def delete(self, key: str, context):
        self.sdk(context).delete_object(Bucket=self.bucket, Key=key)
