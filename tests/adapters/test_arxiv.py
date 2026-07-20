import httpx
import respx

from academic_paper_discovery.adapters.arxiv import ArxivSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <title>Stereo Surgical Tool Pose Estimation</title>
    <summary>We estimate six degree-of-freedom tool pose.</summary>
    <published>2024-01-20T00:00:00Z</published>
    <author><name>Ana Li</name></author>
    <author><name>Bo Zhang</name></author>
    <category term="cs.CV" />
    <arxiv:doi>10.3000/TOOL</arxiv:doi>
    <arxiv:journal_ref>MICCAI 2024</arxiv:journal_ref>
    <link rel="alternate" href="https://arxiv.org/abs/2401.12345v2" />
    <link title="pdf" href="https://arxiv.org/pdf/2401.12345v2" />
  </entry>
</feed>
"""


@respx.mock
def test_arxiv_parses_atom_and_ignores_pdf_link() -> None:
    route = respx.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            content=ATOM_FEED,
        )
    )
    request = SearchRequest.with_defaults(
        topic="stereo surgical tool pose",
        current_year=2026,
        year_from=2022,
        year_to=2026,
        source_limit=10,
    )
    plan = build_query_plan(request)

    with MetadataHttpClient() as client:
        result = ArxivSource(client=client, sleep=lambda _: None).search(plan, request)

    params = route.calls[0].request.url.params
    paper = result.papers[0]
    assert 'all:"stereo surgical tool pose"' in params["search_query"]
    assert params["start"] == "0"
    assert params["max_results"] == "10"
    assert paper.title == "Stereo Surgical Tool Pose Estimation"
    assert paper.authors == ["Ana Li", "Bo Zhang"]
    assert paper.year == 2024
    assert paper.arxiv_id == "2401.12345v2"
    assert paper.doi == "10.3000/tool"
    assert paper.venue == "MICCAI 2024"
    assert [link.url for link in paper.links] == [
        "https://arxiv.org/abs/2401.12345v2"
    ]
    assert len(result.papers) == 1


@respx.mock
def test_arxiv_throttles_repeated_queries() -> None:
    route = respx.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/atom+xml"},
            content=(
                b'<feed xmlns="http://www.w3.org/2005/Atom" '
                b'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
                b"<opensearch:totalResults>0</opensearch:totalResults></feed>"
            ),
        )
    )
    sleeps: list[float] = []
    request = SearchRequest.with_defaults(
        topic="robot autofocus",
        current_year=2026,
        expanded_queries=["microscope autofocus"],
    )
    plan = build_query_plan(request)

    with MetadataHttpClient() as client:
        ArxivSource(client=client, sleep=sleeps.append).search(plan, request)

    assert len(route.calls) == 2
    assert sleeps == [3.0]
