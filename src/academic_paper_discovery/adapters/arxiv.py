"""arXiv Atom API 元数据适配器。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from time import sleep as _default_sleep

from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import Paper, PaperLink, SearchRequest
from academic_paper_discovery.query_plan import QueryPlan


_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivSource:
    """从 arXiv 检索预印本元数据，忽略 PDF 链接。"""

    name = "arXiv"
    endpoint = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        *,
        client: MetadataHttpClient,
        sleep: Callable[[float], None] = _default_sleep,
    ) -> None:
        self.client = client
        self.sleep = sleep

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        papers: list[Paper] = []
        request_count = 0
        try:
            for query in plan.queries:
                offset = 0
                while len(papers) < request.source_limit:
                    if request_count:
                        self.sleep(3.0)
                    remaining = request.source_limit - len(papers)
                    params = {
                        "search_query": _build_query(query, plan, request),
                        "start": offset,
                        "max_results": min(remaining, 100),
                        "sortBy": "relevance",
                        "sortOrder": "descending",
                    }
                    payload = self.client.get(self.endpoint, params=params)
                    request_count += 1
                    root = ET.fromstring(payload.body)
                    entries = root.findall("atom:entry", _NS)
                    papers.extend(self._map_entry(entry) for entry in entries[:remaining])
                    total = _element_int(root.find("opensearch:totalResults", _NS))
                    offset += len(entries)
                    if not entries or offset >= total:
                        break
                if len(papers) >= request.source_limit:
                    break
        except Exception:
            return AdapterResult(papers=papers)

        return AdapterResult(papers=papers)

    def _map_entry(self, entry: ET.Element) -> Paper:
        identifier_url = _element_text(entry.find("atom:id", _NS))
        arxiv_id = identifier_url.rsplit("/", 1)[-1] if identifier_url else None
        published = _element_text(entry.find("atom:published", _NS))
        alternate = None
        for link in entry.findall("atom:link", _NS):
            if link.attrib.get("rel") == "alternate" and link.attrib.get("title") != "pdf":
                alternate = link.attrib.get("href")
                break
        links = (
            [PaperLink(kind="preprint", url=alternate, source=self.name)]
            if alternate
            else []
        )

        return Paper(
            title=_element_text(entry.find("atom:title", _NS)) or "未核验标题",
            authors=[
                name
                for author in entry.findall("atom:author", _NS)
                if (name := _element_text(author.find("atom:name", _NS)))
            ],
            year=_year_from_iso(published),
            venue=_element_text(entry.find("arxiv:journal_ref", _NS)),
            abstract=_element_text(entry.find("atom:summary", _NS)),
            doi=_element_text(entry.find("arxiv:doi", _NS)),
            arxiv_id=arxiv_id,
            publication_type="preprint",
            is_formal=False,
            links=links,
            source_names=[self.name],
            raw_ids={"arxiv": arxiv_id} if arxiv_id else {},
        )


def _build_query(query: str, plan: QueryPlan, request: SearchRequest) -> str:
    escaped = query.replace('"', r'\"')
    parts = [
        f'all:"{escaped}"',
        (
            f"submittedDate:[{request.year_from}01010000 TO "
            f"{request.year_to}12312359]"
        ),
    ]
    parts.extend(f'ANDNOT all:"{term}"' for term in plan.exclusions)
    return " AND ".join(parts)


def _element_text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    cleaned = " ".join(element.text.split())
    return cleaned or None


def _element_int(element: ET.Element | None) -> int:
    try:
        return int(_element_text(element) or 0)
    except ValueError:
        return 0


def _year_from_iso(value: str | None) -> int | None:
    if value and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None
