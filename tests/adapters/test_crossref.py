import httpx
import respx

from academic_paper_discovery.adapters.crossref import CrossrefSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


@respx.mock
def test_crossref_maps_publication_metadata_without_following_paper_links() -> None:
    route = respx.get("https://api.crossref.org/works").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json={
                "message": {
                    "items": [
                        {
                            "title": ["Stereo Tool Tracking"],
                            "author": [{"given": "Ana", "family": "Li"}],
                            "published-print": {"date-parts": [[2024, 1, 2]]},
                            "container-title": ["IEEE TMI"],
                            "abstract": "<jats:p>Tracks surgical tools.</jats:p>",
                            "DOI": "10.1000/ABC",
                            "URL": "https://doi.org/10.1000/ABC",
                            "is-referenced-by-count": 12,
                            "type": "journal-article",
                        }
                    ]
                }
            },
        )
    )
    request = SearchRequest.with_defaults(
        topic="stereo surgical tool tracking",
        current_year=2026,
        year_from=2022,
        year_to=2026,
        source_limit=10,
    )
    plan = build_query_plan(request)

    with MetadataHttpClient() as client:
        result = CrossrefSource(client=client, mailto="user@example.org").search(
            plan,
            request,
        )

    params = route.calls[0].request.url.params
    paper = result.papers[0]
    assert params["query.bibliographic"] == "stereo surgical tool tracking"
    assert params["filter"] == (
        "from-pub-date:2022-01-01,until-pub-date:2026-12-31"
    )
    assert params["rows"] == "10"
    assert params["mailto"] == "user@example.org"
    assert paper.title == "Stereo Tool Tracking"
    assert paper.authors == ["Ana Li"]
    assert paper.year == 2024
    assert paper.venue == "IEEE TMI"
    assert paper.abstract == "Tracks surgical tools."
    assert paper.doi == "10.1000/abc"
    assert paper.citation_count == 12
    assert result.status.state == "success"
    assert len(route.calls) == 1
