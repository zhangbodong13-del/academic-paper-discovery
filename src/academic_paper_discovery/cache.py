"""仅保存学术元数据响应的本地缓存。"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Mapping


_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/atom+xml",
    "text/xml",
    "text/plain",
}


class MetadataCache:
    """带过期时间的元数据缓存。"""

    def __init__(self, root: Path, *, max_payload_bytes: int = 10_000_000) -> None:
        self.root = Path(root)
        self.max_payload_bytes = max_payload_bytes

    @staticmethod
    def make_key(source: str, params: Mapping[str, object]) -> str:
        canonical = json.dumps(
            {"source": source, "params": dict(params)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def entry_path(self, key: str) -> Path:
        safe_name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{safe_name}.json"

    def put(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str,
        ttl_seconds: int,
        now: float | None = None,
    ) -> None:
        normalized_type = content_type.split(";", 1)[0].strip().lower()
        if (
            normalized_type not in _ALLOWED_CONTENT_TYPES
            or payload.lstrip().startswith(b"%PDF")
        ):
            raise ValueError("仅允许缓存元数据，禁止缓存论文或 PDF")
        if len(payload) > self.max_payload_bytes:
            raise ValueError("元数据响应超过缓存大小限制")

        timestamp = time.time() if now is None else now
        document = {
            "expires_at": timestamp + ttl_seconds,
            "content_type": normalized_type,
            "body": base64.b64encode(payload).decode("ascii"),
        }
        path = self.entry_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    def get(self, key: str, *, now: float | None = None) -> bytes | None:
        path = self.entry_path(key)
        if not path.exists():
            return None

        timestamp = time.time() if now is None else now
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            if float(document["expires_at"]) < timestamp:
                path.unlink(missing_ok=True)
                return None
            content_type = str(document["content_type"])
            payload = base64.b64decode(document["body"], validate=True)
            if content_type not in _ALLOWED_CONTENT_TYPES:
                raise ValueError("非法缓存类型")
            return payload
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None
