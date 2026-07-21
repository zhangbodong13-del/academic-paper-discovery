"""论文期刊和会议影响力指标解析。"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from importlib import resources
from pathlib import Path
from academic_paper_discovery.http import MetadataHttpClient

OnlineLookup = Callable[[str], str | None]


def _normalize_venue(venue: str) -> str:
    """统一大小写和多余空格，便于场所名称匹配。"""

    return re.sub(r"\s+", " ", venue).strip().casefold()


def load_local_metrics(path: str | Path) -> dict[str, str]:
    """从 UTF-8 JSON 文件读取本地影响力指标。"""

    data = json.loads(
        Path(path).read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError("影响力指标配置必须是 JSON 对象")

    metrics: dict[str, str] = {}

    for venue, metric in data.items():
        if not isinstance(venue, str) or not isinstance(metric, str):
            raise ValueError("影响力指标的场所名称和值必须是字符串")

        metrics[venue] = metric

    return metrics
def load_bundled_metrics() -> dict[str, str]:
    """读取项目内置的影响力指标配置。"""

    config_file = resources.files(
        "academic_paper_discovery"
    ).joinpath(
        "data",
        "impact_metrics.json",
    )

    data = json.loads(
        config_file.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError("内置影响力指标配置必须是 JSON 对象")

    metrics: dict[str, str] = {}

    for venue, metric in data.items():
        if not isinstance(venue, str) or not isinstance(metric, str):
            raise ValueError("影响力指标的场所名称和值必须是字符串")

        metrics[venue] = metric

    return metrics

def resolve_impact_metric(
    venue: str | None,
    *,
    local_metrics: Mapping[str, str],
    online_lookup: OnlineLookup | None = None,
) -> str:
    """优先读取本地指标，本地缺失时调用联网查询函数。"""

    if venue is None or not venue.strip():
        return "未核验"

    cleaned_venue = re.sub(r"\s+", " ", venue).strip()
    normalized_venue = _normalize_venue(cleaned_venue)

    for local_venue, metric in local_metrics.items():
        if _normalize_venue(local_venue) == normalized_venue:
            return metric.strip() if metric.strip() else "未核验"

    if online_lookup is not None:
        try:
            online_metric = online_lookup(cleaned_venue)
        except Exception:
            return "未核验"

        if online_metric and online_metric.strip():
            return online_metric.strip()

    return "未核验"
class RemoteImpactLookup:
    """从远程 JSON 指标表查询场所影响力，并缓存首次响应。"""

    def __init__(
        self,
        *,
        client: MetadataHttpClient,
        url: str,
    ) -> None:
        cleaned_url = url.strip()

        if not cleaned_url:
            raise ValueError("远程影响力指标 URL 不能为空")

        self.client = client
        self.url = cleaned_url
        self._metrics: dict[str, str] | None = None

    def __call__(self, venue: str) -> str | None:
        if self._metrics is None:
            self._metrics = self._load_metrics()

        normalized_venue = _normalize_venue(venue)

        for remote_venue, metric in self._metrics.items():
            if _normalize_venue(remote_venue) == normalized_venue:
                cleaned_metric = metric.strip()
                return cleaned_metric or None

        return None

    def _load_metrics(self) -> dict[str, str]:
        payload = self.client.get(self.url)
        data = json.loads(payload.body)

        if not isinstance(data, dict):
            raise ValueError("远程影响力指标必须是 JSON 对象")

        metrics: dict[str, str] = {}

        for venue, metric in data.items():
            if not isinstance(venue, str) or not isinstance(metric, str):
                raise ValueError(
                    "远程影响力指标的场所名称和值必须是字符串"
                )

            metrics[venue] = metric

        return metrics