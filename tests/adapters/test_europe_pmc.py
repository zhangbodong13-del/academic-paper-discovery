import httpx
import respx

from academic_paper_discovery.adapters.europe_pmc import EuropePmcSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


@respx.mock
def test_europe_pmc_maps_core_metadata_and_year_query() -> None:
    route = respx.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    ).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "hitCount": 1,
                "nextCursorMark": "next",
                "resultList": {
                    "result": [
                        {
                            "title": "Microsurgical Instrument Pose Estimation",
                            "authorList": {
                                "author": [
                                    {"fullName": "Bo Zhang"},
                                    {"fullName": "Alice Smith"},
                                ]
                            },
                            "pubYear": "2025",
                            "journalTitle": "Medical Image Analysis",
                            "doi": "10.2000/POSE",
                            "pmid": "12345678",
                            "citedByCount": 7,
                            "abstractText": "Estimates tool pose from stereo images.",
                            "pubTypeList": {"pubType": ["research article"]},
                        }
                    ]
                },
            },
        )
    )
    request = SearchRequest.with_defaults(
        topic="microsurgical instrument pose",
        current_year=2026,
        year_from=2022,
        year_to=2026,
        source_limit=5,
    )
    plan = build_query_plan(request)

    with MetadataHttpClient() as client:
        result = EuropePmcSource(client=client).search(plan, request)

    params = route.calls[0].request.url.params
    paper = result.papers[0]
    assert "FIRST_PDATE:[2022-01-01 TO 2026-12-31]" in params["query"]
    assert params["format"] == "json"
    assert params["resultType"] == "core"
    assert params["pageSize"] == "5"
    assert paper.title == "Microsurgical Instrument Pose Estimation"
    assert paper.authors == ["Bo Zhang", "Alice Smith"]
    assert paper.year == 2025
    assert paper.venue == "Medical Image Analysis"
    assert paper.doi == "10.2000/pose"
    assert paper.raw_ids["pmid"] == "12345678"
    assert paper.citation_count == 7
    assert paper.abstract == "Estimates tool pose from stereo images."
    assert len(result.papers) == 1
    assert len(route.calls) == 1
