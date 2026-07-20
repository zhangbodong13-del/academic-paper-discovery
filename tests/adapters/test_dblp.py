import httpx
import respx

from academic_paper_discovery.adapters.dblp import DblpSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


@respx.mock
def test_dblp_maps_publication_json_without_opening_electronic_links() -> None:
    route = respx.get("https://dblp.org/search/publ/api").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "result": {
                    "hits": {
                        "@total": "1",
                        "hit": [
                            {
                                "info": {
                                    "authors": {
                                        "author": [
                                            {"text": "Ana Li"},
                                            {"text": "Bo Zhang"},
                                        ]
                                    },
                                    "title": "Robot Microscope Autofocus",
                                    "year": "2023",
                                    "venue": "ICRA",
                                    "type": "Conference and Workshop Papers",
                                    "doi": "10.4000/AUTOFOCUS",
                                    "url": "https://dblp.org/rec/conf/icra/example",
                                    "ee": [
                                        "https://doi.org/10.4000/AUTOFOCUS",
                                        "https://example.org/project",
                                    ],
                                }
                            }
                        ],
                    }
                }
            },
        )
    )
    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2026,
        source_limit=8,
    )
    plan = build_query_plan(request)

    with MetadataHttpClient() as client:
        result = DblpSource(client=client).search(plan, request)

    params = route.calls[0].request.url.params
    paper = result.papers[0]
    assert params["q"] == "robot microscope autofocus"
    assert params["format"] == "json"
    assert params["h"] == "8"
    assert params["f"] == "0"
    assert params["c"] == "0"
    assert paper.title == "Robot Microscope Autofocus"
    assert paper.authors == ["Ana Li", "Bo Zhang"]
    assert paper.year == 2023
    assert paper.venue == "ICRA"
    assert paper.doi == "10.4000/autofocus"
    assert len(paper.links) == 3
    assert len(route.calls) == 1
