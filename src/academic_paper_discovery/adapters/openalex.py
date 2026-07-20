"""需要 API Key 的 OpenAlex 可选元数据适配器。"""

from __future__ import annotations

import json
import time
from typing import Any

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest, SourceStatus
from academic_paper_discovery.query_plan import QueryPlan


class OpenAlexSource:
    """使用可选免费 Key 增强论文元数据。"""

    name = "OpenAlex"
    endpoint = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        client: MetadataHttpClient | None,
        api_key: str | None,
    ) -> None:
        self.client = client
        self.api_key = api_key.strip() if api_key else None

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        if not self.api_key:
            return AdapterResult(
                status=SourceStatus(
                    source=self.name,
                    state="skipped",
                    message="未配置 OpenAlex API Key，已跳过可选增强来源",
                )
            )
        if self.client is None:
            return AdapterResult(
                status=SourceStatus(
                    source=self.name,
                    state="failed",
                    message="OpenAlex HTTP 客户端未配置",
                )
            )

        started = time.perf_counter()
        papers: list[Paper] = []
        try:
            for query in plan.queries:
                remaining = request.source_limit - len(papers)
                if remaining <= 0:
                    break
                payload = self.client.get(
                    self.endpoint,
                    params={
                        "api_key": self.api_key,
                        "search": query,
                        "filter": (
                            f"from_publication_date:{request.year_from}-01-01,"
                            f"to_publication_date:{request.year_to}-12-31"
                        ),
                        "per-page": min(remaining, 100),
                    },
                )
                document = json.loads(payload.body)
                papers.extend(
                    self._map_work(work)
                    for work in document.get("results", [])[:remaining]
                )
        except Exception as exc:
            return _status_result(self.name, "failed", papers, started, str(exc))

        return _status_result(self.name, "success", papers, started, "元数据检索完成")

    def _map_work(self, work: dict[str, Any]) -> Paper:
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        openalex_id = str(work.get("id") or "").rsplit("/", 1)[-1] or None
        landing_url = location.get("landing_page_url")
        links = (
            [PaperLink(kind="publisher", url=landing_url, source=self.name)]
            if isinstance(landing_url, str)
            else []
        )
        authors = [
            str(authorship.get("author", {}).get("display_name")).strip()
            for authorship in work.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        work_type = work.get("type")
        return Paper(
            title=str(work.get("display_name") or "未核验标题"),
            authors=authors,
            year=_to_int(work.get("publication_year")),
            venue=source.get("display_name"),
            abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
            doi=work.get("doi"),
            citation_count=_to_int(work.get("cited_by_count")),
            publication_type=work_type,
            is_formal=work_type not in {None, "preprint", "posted-content"},
            links=links,
            source_names=[self.name],
            raw_ids={"openalex": openalex_id} if openalex_id else {},
        )


def _reconstruct_abstract(index: object) -> str | None:
    if not isinstance(index, dict) or not index:
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        positioned.extend((position, word) for position in positions if isinstance(position, int))
    if not positioned:
        return None
    return " ".join(word for _, word in sorted(positioned))


def _to_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _status_result(
    source: str,
    state: str,
    papers: list[Paper],
    started: float,
    message: str,
) -> AdapterResult:
    return AdapterResult(
        papers=papers,
        status=SourceStatus(
            source=source,
            state=state,  # type: ignore[arg-type]
            result_count=len(papers),
            message=f"{source} {message}",
            elapsed_ms=max(0, int((time.perf_counter() - started) * 1000)),
        ),
    )
