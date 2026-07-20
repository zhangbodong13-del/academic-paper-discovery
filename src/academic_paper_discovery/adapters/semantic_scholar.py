"""需要 API Key 的 Semantic Scholar 可选元数据适配器。"""

from __future__ import annotations

import json
from typing import Any

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest
from academic_paper_discovery.query_plan import QueryPlan


class SemanticScholarSource:
    """使用可选 Key 增强引用量、摘要和开放获取网址。"""

    name = "Semantic Scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = (
        "paperId,title,abstract,year,venue,publicationTypes,citationCount,"
        "externalIds,url,openAccessPdf,authors"
    )

    def __init__(
        self,
        *,
        client: MetadataHttpClient | None,
        api_key: str | None,
    ) -> None:
        self.client = client
        self.api_key = api_key.strip() if api_key else None

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        if not self.api_key or self.client is None:
            return AdapterResult()

        papers: list[Paper] = []
        try:
            for query in plan.queries:
                remaining = request.source_limit - len(papers)
                if remaining <= 0:
                    break
                payload = self.client.get(
                    self.endpoint,
                    params={
                        "query": query,
                        "limit": min(remaining, 100),
                        "fields": self.fields,
                        "year": f"{request.year_from}-{request.year_to}",
                    },
                    headers={"x-api-key": self.api_key},
                )
                document = json.loads(payload.body)
                papers.extend(
                    self._map_paper(item)
                    for item in document.get("data", [])[:remaining]
                )
        except Exception:
            return AdapterResult(papers=papers)

        return AdapterResult(papers=papers)

    def _map_paper(self, item: dict[str, Any]) -> Paper:
        external_ids = item.get("externalIds") or {}
        urls = [
            ("index", item.get("url")),
            ("open-access", (item.get("openAccessPdf") or {}).get("url")),
        ]
        links = [
            PaperLink(kind=kind, url=url, source=self.name)
            for kind, url in urls
            if isinstance(url, str) and url.startswith(("http://", "https://"))
        ]
        publication_types = item.get("publicationTypes") or []
        if isinstance(publication_types, str):
            publication_types = [publication_types]
        publication_type = ", ".join(publication_types) or None
        return Paper(
            title=str(item.get("title") or "未核验标题"),
            authors=[
                str(author.get("name")).strip()
                for author in item.get("authors", [])
                if author.get("name")
            ],
            year=_to_int(item.get("year")),
            venue=item.get("venue") or None,
            abstract=item.get("abstract") or None,
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            citation_count=_to_int(item.get("citationCount")),
            publication_type=publication_type,
            is_formal=publication_type is not None and "preprint" not in publication_type.lower(),
            links=links,
            source_names=[self.name],
            raw_ids={"semantic_scholar": str(item.get("paperId"))},
        )


def _to_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None
