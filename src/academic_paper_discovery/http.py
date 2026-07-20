"""只允许学术元数据的 HTTP 访问层。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Mapping

import httpx


_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/atom+xml",
    "text/xml",
    "text/plain",
}


class MetadataOnlyError(RuntimeError):
    """远程响应不是允许的元数据格式。"""


@dataclass(frozen=True, slots=True)
class MetadataPayload:
    body: bytes
    content_type: str


class MetadataHttpClient:
    """带有限重试和响应类型检查的同步 HTTP 客户端。"""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 20.0,
        retries: int = 2,
        max_response_bytes: int = 10_000_000,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._owns_client = client is None
        self.retries = retries
        self.max_response_bytes = max_response_bytes
        self.sleep = sleep

    def __enter__(self) -> MetadataHttpClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> MetadataPayload:
        response: httpx.Response | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._client.get(url, params=params, headers=headers)
            except httpx.RequestError:
                if attempt >= self.retries:
                    raise
                self.sleep(2**attempt)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.retries:
                    self.sleep(2**attempt)
                    continue
            response.raise_for_status()
            break

        if response is None:  # pragma: no cover - loop guarantees a response or exception
            raise RuntimeError("未收到 HTTP 响应")

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        body = response.content
        if content_type not in _ALLOWED_CONTENT_TYPES or body.lstrip().startswith(b"%PDF"):
            raise MetadataOnlyError("不允许下载论文或 PDF，仅接受元数据响应")
        if len(body) > self.max_response_bytes:
            raise MetadataOnlyError("元数据响应超过允许大小")
        return MetadataPayload(body=body, content_type=content_type)
