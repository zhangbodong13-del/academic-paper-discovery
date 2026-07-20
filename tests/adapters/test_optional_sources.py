import httpx
import pytest
import respx

from academic_paper_discovery.adapters.openalex import OpenAlexSource
from academic_paper_discovery.adapters.semantic_scholar import SemanticScholarSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


def _request_and_plan():
    request = SearchRequest.with_defaults(
        topic="robot autofocus",
        current_year=2026,
        year_from=2022,
        year_to=2026,
        source_limit=5,
    )
    return request, build_query_plan(request)


@pytest.mark.parametrize("source_type", [OpenAlexSource, SemanticScholarSource])
def test_optional_source_skips_without_key(source_type) -> None:
    request, plan = _request_and_plan()

    result = source_type(client=None, api_key=None).search(plan, request)

    assert result.papers == []
    assert result.status.state == "skipped"
    assert "API Key" in result.status.message


@respx.mock
def test_openalex_uses_key_and_reconstructs_abstract() -> None:
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "display_name": "Robot Microscope Autofocus",
                        "publication_year": 2025,
                        "doi": "https://doi.org/10.5000/AUTO",
                        "type": "article",
                        "cited_by_count": 4,
                        "authorships": [
                            {"author": {"display_name": "Ana Li"}}
                        ],
                        "primary_location": {
                            "landing_page_url": "https://doi.org/10.5000/AUTO",
                            "source": {"display_name": "Nature Methods"},
                        },
                        "abstract_inverted_index": {
                            "Automatic": [0],
                            "microscope": [1],
                            "focusing": [2],
                        },
                    }
                ],
                "meta": {"count": 1},
            },
        )
    )
    request, plan = _request_and_plan()

    with MetadataHttpClient() as client:
        result = OpenAlexSource(client=client, api_key="openalex-key").search(
            plan,
            request,
        )

    params = route.calls[0].request.url.params
    paper = result.papers[0]
    assert params["api_key"] == "openalex-key"
    assert params["search"] == "robot autofocus"
    assert paper.abstract == "Automatic microscope focusing"
    assert paper.venue == "Nature Methods"
    assert paper.raw_ids["openalex"] == "W123"


@respx.mock
def test_semantic_scholar_uses_header_and_maps_metadata_links() -> None:
    route = respx.get(
        "https://api.semanticscholar.org/graph/v1/paper/search"
    ).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "total": 1,
                "data": [
                    {
                        "paperId": "s2-123",
                        "title": "Robot Microscope Autofocus",
                        "abstract": "Focuses a robotic microscope.",
                        "year": 2025,
                        "venue": "ICRA",
                        "publicationTypes": ["Conference"],
                        "citationCount": 3,
                        "externalIds": {
                            "DOI": "10.6000/AUTO",
                            "ArXiv": "2501.00001",
                        },
                        "url": "https://www.semanticscholar.org/paper/s2-123",
                        "openAccessPdf": {
                            "url": "https://arxiv.org/pdf/2501.00001"
                        },
                        "authors": [{"name": "Bo Zhang"}],
                    }
                ],
            },
        )
    )
    request, plan = _request_and_plan()

    with MetadataHttpClient() as client:
        result = SemanticScholarSource(client=client, api_key="s2-key").search(
            plan,
            request,
        )

    sent_request = route.calls[0].request
    paper = result.papers[0]
    assert sent_request.headers["x-api-key"] == "s2-key"
    assert sent_request.url.params["query"] == "robot autofocus"
    assert paper.doi == "10.6000/auto"
    assert paper.arxiv_id == "2501.00001"
    assert len(paper.links) == 2
    assert len(route.calls) == 1
