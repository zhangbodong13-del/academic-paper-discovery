import json
from pathlib import Path

import httpx
import respx

from academic_paper_discovery.adapters.arxiv import ArxivSource
from academic_paper_discovery.adapters.crossref import CrossrefSource
from academic_paper_discovery.adapters.dblp import DblpSource
from academic_paper_discovery.adapters.europe_pmc import EuropePmcSource
from academic_paper_discovery.http import MetadataHttpClient
from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.pipeline import SearchPipeline
from academic_paper_discovery.reporting import render_markdown, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]


ARXIV_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>https://arxiv.org/abs/2401.12345v2</id>
    <title>Stereo Surgical Instrument Pose Estimation</title>
    <summary>Six degree-of-freedom pose from stereo surgical video.</summary>
    <published>2024-01-20T00:00:00Z</published>
    <author><name>Ana Li</name></author>
    <category term="cs.CV" />
    <arxiv:doi>10.1000/stereo-pose</arxiv:doi>
    <arxiv:journal_ref>MICCAI 2024</arxiv:journal_ref>
    <link rel="alternate" href="https://arxiv.org/abs/2401.12345v2" />
    <link title="pdf" href="https://arxiv.org/pdf/2401.12345v2" />
  </entry>
</feed>
"""


@respx.mock
def test_four_source_end_to_end_report_never_downloads_full_text(tmp_path) -> None:
    request_payload = json.loads(
        (ROOT / "tests" / "fixtures" / "end_to_end_request.json").read_text(
            encoding="utf-8"
        )
    )
    request = SearchRequest.model_validate(request_payload)

    routes = [
        respx.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                json={
                    "message": {
                        "items": [
                            {
                                "title": ["Stereo Surgical Instrument Pose Estimation"],
                                "author": [{"given": "Ana", "family": "Li"}],
                                "published-print": {"date-parts": [[2024]]},
                                "container-title": ["MICCAI"],
                                "abstract": "Stereo surgical instrument pose estimation.",
                                "DOI": "10.1000/STEREO-POSE",
                                "URL": "https://doi.org/10.1000/STEREO-POSE",
                                "is-referenced-by-count": 18,
                                "type": "proceedings-article",
                            },
                            {
                                "title": ["Learning Surgical Tool Geometry"],
                                "author": [{"given": "Bo", "family": "Zhang"}],
                                "published-online": {"date-parts": [[2025]]},
                                "container-title": ["Medical Image Analysis"],
                                "DOI": "10.1000/GEOMETRY",
                                "URL": "https://doi.org/10.1000/GEOMETRY",
                                "type": "journal-article",
                            },
                        ]
                    }
                },
            )
        ),
        respx.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        ).mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                json={
                    "hitCount": 1,
                    "resultList": {
                        "result": [
                            {
                                "title": "Markerless Instrument Tracking in Surgery",
                                "authorList": {
                                    "author": [{"fullName": "Chen Wang"}]
                                },
                                "pubYear": "2023",
                                "journalTitle": "IEEE TMI",
                                "doi": "10.1000/MARKERLESS",
                                "abstractText": "Markerless pose estimation.",
                            }
                        ]
                    },
                },
            )
        ),
        respx.get("https://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "application/atom+xml"},
                content=ARXIV_FEED,
            )
        ),
        respx.get("https://dblp.org/search/publ/api").mock(
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
                                            "author": [{"text": "Dana Smith"}]
                                        },
                                        "title": "Six-DoF Surgical Instrument Tracking",
                                        "year": "2022",
                                        "venue": "MICCAI",
                                        "type": "Conference and Workshop Papers",
                                        "doi": "10.1000/SIXDOF",
                                        "url": "https://dblp.org/rec/conf/miccai/sixdof",
                                    }
                                }
                            ],
                        }
                    }
                },
            )
        ),
    ]

    with MetadataHttpClient() as client:
        result = SearchPipeline(
            [
                CrossrefSource(client=client),
                EuropePmcSource(client=client),
                ArxivSource(client=client, sleep=lambda _: None),
                DblpSource(client=client),
            ],
            current_year=2026,
        ).run(request)

    output = tmp_path / "e2e-output"
    output.mkdir()
    (output / "report.md").write_text(render_markdown(result), encoding="utf-8")
    write_csv(result, output / "report.csv")
    write_json(result, output / "report.json")

    assert all(route.called for route in routes)
    assert len(result.papers) == 4
    merged = next(paper for paper in result.papers if paper.doi == "10.1000/stereo-pose")
    assert merged.source_names == ["Crossref", "arXiv"]
    assert [status.source for status in result.source_statuses] == [
        "Crossref",
        "Europe PMC",
        "arXiv",
        "DBLP",
    ]
    assert all(status.state == "success" for status in result.source_statuses)
    assert len(result.papers) <= 20

    report = (output / "report.md").read_text(encoding="utf-8")
    assert report.index("## 必读") < report.index("## 强相关")
    assert report.index("## 强相关") < report.index("## 拓展阅读")
    assert report.index("## 论文对比表") < report.index("## 论文网址")
    assert "本次检索未筛选出该层级论文。" in report

    generated_files = [path for path in output.rglob("*") if path.is_file()]
    assert {path.suffix for path in generated_files} == {".md", ".csv", ".json"}
    assert not any("fulltext" in path.name.casefold() for path in generated_files)
    assert not any(path.read_bytes().lstrip().startswith(b"%PDF") for path in generated_files)
    assert "arxiv.org/pdf/" not in report
