"""Crossref 公共 REST API 元数据适配器。"""

from __future__ import annotations

import html
import json
import re
import time
from typing import Any

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest, SourceStatus
from academic_paper_discovery.query_plan import QueryPlan


class CrossrefSource:
    """从 Crossref 检索出版物元数据。"""

    name = "Crossref"
    endpoint = "https://api.crossref.org/works"

    def __init__(self, *, client: MetadataHttpClient, mailto: str | None = None) -> None:
        self.client = client
        self.mailto = mailto.strip() if mailto else None

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        started = time.perf_counter()
        papers: list[Paper] = []
        try:
            for query in plan.queries:
                remaining = request.source_limit - len(papers)
                if remaining <= 0:
                    break
                params: dict[str, object] = {
                    "query.bibliographic": query,
                    "filter": (
                        f"from-pub-date:{request.year_from}-01-01,"
                        f"until-pub-date:{request.year_to}-12-31"
                    ),
                    "rows": remaining,
                }
                if self.mailto:
                    params["mailto"] = self.mailto
                payload = self.client.get(
                    self.endpoint,
                    params=params,
                    headers={
                        "User-Agent": (
                            "academic-paper-discovery/0.1 "
                            "(metadata-only literature search)"
                        )
                    },
                )
                document = json.loads(payload.body)
                items = document.get("message", {}).get("items", [])
                papers.extend(self._map_item(item) for item in items[:remaining])
        except Exception as exc:
            return AdapterResult(
                papers=papers,
                status=SourceStatus(
                    source=self.name,
                    state="failed",
                    result_count=len(papers),
                    message=f"Crossref 元数据请求失败：{exc}",
                    elapsed_ms=_elapsed_ms(started),
                ),
            )

        return AdapterResult(
            papers=papers,
            status=SourceStatus(
                source=self.name,
                state="success",
                result_count=len(papers),
                message="Crossref 元数据检索完成",
                elapsed_ms=_elapsed_ms(started),
            ),
        )

    def _map_item(self, item: dict[str, Any]) -> Paper:
        doi = item.get("DOI")
        url = item.get("URL")
        links = []
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            links.append(PaperLink(kind="publisher", url=url, source=self.name))

        publication_type = item.get("type")
        return Paper(
            title=_first_text(item.get("title")) or "未核验标题",
            authors=_crossref_authors(item.get("author", [])),
            year=_crossref_year(item),
            venue=_first_text(item.get("container-title")),
            abstract=_strip_markup(item.get("abstract")),
            doi=doi,
            citation_count=_nonnegative_int(item.get("is-referenced-by-count")),
            publication_type=publication_type,
            is_formal=publication_type not in {None, "posted-content"},
            links=links,
            source_names=[self.name],
            raw_ids={"doi": str(doi)} if doi else {},
        )


def _first_text(value: object) -> str | None:
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return cleaned or None
    return None


def _crossref_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = " ".join(
            part.strip()
            for part in (str(author.get("given", "")), str(author.get("family", "")))
            if part.strip()
        )
        if name:
            authors.append(name)
    return authors


def _crossref_year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = item.get(field, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            return _nonnegative_int(date_parts[0][0])
    return None


def _strip_markup(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    without_tags = re.sub(r"<[^>]+>", " ", value)
    cleaned = " ".join(html.unescape(without_tags).split())
    return cleaned or None


def _nonnegative_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
