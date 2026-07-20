"""DBLP 计算机科学出版物检索 API 适配器。"""

from __future__ import annotations

import json
from typing import Any

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest
from academic_paper_discovery.query_plan import QueryPlan


class DblpSource:
    """从 DBLP 检索计算机科学论文元数据。"""

    name = "DBLP"
    endpoint = "https://dblp.org/search/publ/api"

    def __init__(self, *, client: MetadataHttpClient) -> None:
        self.client = client

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        papers: list[Paper] = []
        try:
            for query in plan.queries:
                offset = 0
                while len(papers) < request.source_limit:
                    remaining = request.source_limit - len(papers)
                    params = {
                        "q": query,
                        "format": "json",
                        "h": min(remaining, 1000),
                        "f": offset,
                        "c": 0,
                    }
                    payload = self.client.get(self.endpoint, params=params)
                    document = json.loads(payload.body)
                    hits_document = document.get("result", {}).get("hits", {})
                    hits = hits_document.get("hit", [])
                    if isinstance(hits, dict):
                        hits = [hits]
                    mapped = [self._map_hit(hit) for hit in hits[:remaining]]
                    papers.extend(
                        paper
                        for paper in mapped
                        if paper.year is None
                        or request.year_from <= paper.year <= request.year_to
                    )
                    total = _to_int(hits_document.get("@total")) or 0
                    offset += len(hits)
                    if not hits or offset >= total:
                        break
                if len(papers) >= request.source_limit:
                    break
        except Exception:
            return AdapterResult(papers=papers)

        return AdapterResult(papers=papers)

    def _map_hit(self, hit: dict[str, Any]) -> Paper:
        info = hit.get("info", {})
        doi = info.get("doi")
        urls = _stable_urls([info.get("url"), *_as_list(info.get("ee"))])
        links = [
            PaperLink(
                kind="index" if "dblp.org" in url else "external",
                url=url,
                source=self.name,
            )
            for url in urls
        ]
        return Paper(
            title=_clean_text(info.get("title")) or "未核验标题",
            authors=_dblp_authors(info.get("authors", {}).get("author", [])),
            year=_to_int(info.get("year")),
            venue=_clean_text(info.get("venue")),
            doi=doi,
            publication_type=_clean_text(info.get("type")),
            is_formal=True,
            links=links,
            source_names=[self.name],
            raw_ids={"doi": str(doi)} if doi else {},
        )


def _dblp_authors(value: object) -> list[str]:
    authors: list[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            text = item.get("text")
        else:
            text = item
        cleaned = _clean_text(text)
        if cleaned:
            authors.append(cleaned)
    return authors


def _as_list(value: object) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _stable_urls(values: list[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.startswith(("http://", "https://")):
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).rstrip(".")
    return cleaned or None


def _to_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
