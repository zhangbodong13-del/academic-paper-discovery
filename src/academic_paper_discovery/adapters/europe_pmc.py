"""Europe PMC 公共检索 API 元数据适配器。"""

from __future__ import annotations

import json
import time
from typing import Any

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest, SourceStatus
from academic_paper_discovery.query_plan import QueryPlan


class EuropePmcSource:
    """从 Europe PMC 检索生命科学与医学论文元数据。"""

    name = "Europe PMC"
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, *, client: MetadataHttpClient) -> None:
        self.client = client

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        started = time.perf_counter()
        papers: list[Paper] = []
        try:
            for query in plan.queries:
                cursor = "*"
                fetched_for_query = 0
                while len(papers) < request.source_limit:
                    remaining = request.source_limit - len(papers)
                    params = {
                        "query": _build_query(query, plan, request),
                        "format": "json",
                        "resultType": "core",
                        "pageSize": remaining,
                        "cursorMark": cursor,
                    }
                    payload = self.client.get(self.endpoint, params=params)
                    document = json.loads(payload.body)
                    results = document.get("resultList", {}).get("result", [])
                    papers.extend(self._map_item(item) for item in results[:remaining])
                    fetched_for_query += len(results)
                    hit_count = _nonnegative_int(document.get("hitCount")) or 0
                    next_cursor = document.get("nextCursorMark")
                    if (
                        not results
                        or fetched_for_query >= hit_count
                        or not next_cursor
                        or next_cursor == cursor
                    ):
                        break
                    cursor = str(next_cursor)
                if len(papers) >= request.source_limit:
                    break
        except Exception as exc:
            return AdapterResult(
                papers=papers,
                status=SourceStatus(
                    source=self.name,
                    state="failed",
                    result_count=len(papers),
                    message=f"Europe PMC 元数据请求失败：{exc}",
                    elapsed_ms=_elapsed_ms(started),
                ),
            )

        return AdapterResult(
            papers=papers,
            status=SourceStatus(
                source=self.name,
                state="success",
                result_count=len(papers),
                message="Europe PMC 元数据检索完成",
                elapsed_ms=_elapsed_ms(started),
            ),
        )

    def _map_item(self, item: dict[str, Any]) -> Paper:
        doi = item.get("doi")
        pmid = item.get("pmid") or item.get("id")
        url = (
            f"https://doi.org/{doi}"
            if doi
            else f"https://europepmc.org/article/MED/{pmid}"
            if pmid
            else None
        )
        links = [PaperLink(kind="publisher", url=url, source=self.name)] if url else []
        publication_types = item.get("pubTypeList", {}).get("pubType", [])
        if isinstance(publication_types, str):
            publication_types = [publication_types]

        return Paper(
            title=str(item.get("title") or "未核验标题"),
            authors=_authors(item),
            year=_nonnegative_int(item.get("pubYear")),
            venue=_journal_title(item),
            abstract=_clean_text(item.get("abstractText")),
            doi=doi,
            citation_count=_nonnegative_int(item.get("citedByCount")),
            publication_type=", ".join(publication_types) or None,
            is_formal=True,
            links=links,
            source_names=[self.name],
            raw_ids={"pmid": str(pmid)} if pmid else {},
        )


def _build_query(query: str, plan: QueryPlan, request: SearchRequest) -> str:
    parts = [
        f"({query})",
        f"FIRST_PDATE:[{request.year_from}-01-01 TO {request.year_to}-12-31]",
    ]
    parts.extend(f'NOT ("{term}")' for term in plan.exclusions)
    return " AND ".join(parts)


def _authors(item: dict[str, Any]) -> list[str]:
    values = item.get("authorList", {}).get("author", [])
    if not isinstance(values, list):
        return []
    return [
        str(author["fullName"]).strip()
        for author in values
        if isinstance(author, dict) and author.get("fullName")
    ]


def _journal_title(item: dict[str, Any]) -> str | None:
    direct = item.get("journalTitle")
    if direct:
        return str(direct).strip() or None
    nested = item.get("journalInfo", {}).get("journal", {}).get("title")
    return str(nested).strip() if nested else None


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _nonnegative_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
