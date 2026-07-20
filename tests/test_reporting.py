import csv
import json
import re
from pathlib import Path

import pytest

from academic_paper_discovery.models import (
    Paper,
    PaperLink,
    RecommendationTier,
    SearchRequest,
    SearchResult,
)
from academic_paper_discovery.reporting import (
    _code_url,
    _primary_paper_url,
    render_markdown,
    write_csv,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_HEADINGS = [
    "必读",
    "强相关",
    "拓展阅读",
    "论文对比表",
    "局限与下一步",
]


@pytest.fixture
def sample_result() -> SearchResult:
    request = SearchRequest.with_defaults(
        topic="机器人显微镜自动对焦",
        current_year=2026,
        expanded_queries=["robot microscope autofocus"],
    )
    return SearchResult(
        request=request,
        papers=[
            Paper(
                title="Paper | One",
                authors=["Ada Lovelace", "张三"],
                year=2025,
                venue="Nature Methods",
                abstract="Autofocus for robotic microscopy.",
                doi="10.1000/one",
                links=[
                    PaperLink(
                        kind="publisher",
                        url="https://example.org/paper/one?full=true",
                        source="crossref",
                        verified=True,
                    ),
                    PaperLink(
                        kind="code",
                        url="https://github.com/example/paper-one",
                        source="semantic-scholar",
                    ),
                ],
                source_names=["crossref", "semantic-scholar"],
                score=0.9,
                tier=RecommendationTier.MUST_READ,
                why_read="与核心主题直接相关",
            ),
            Paper(
                title="Paper Two",
                year=2022,
                doi="10.1000/two",
                source_names=["europe-pmc"],
                score=0.66,
                tier=RecommendationTier.STRONG,
                why_read="提供互补方法",
            ),
            Paper(
                title="Paper Three",
                source_names=["dblp"],
                score=0.3,
                tier=RecommendationTier.EXPLORATORY,
                why_read="用于拓展阅读",
            ),
        ],
        query_plan={
            "original_topic": "机器人显微镜自动对焦",
            "queries": ["机器人显微镜自动对焦", "robot microscope autofocus"],
            "venue_queries": [],
            "exclusions": [],
            "year_from": 2022,
            "year_to": 2026,
            "assumptions": ["默认年份范围：2022-2026"],
        },
        total_candidates=23,
    )


def test_markdown_has_only_requested_sections_in_order(
    sample_result: SearchResult,
) -> None:
    report = render_markdown(sample_result)

    assert re.findall(r"^## (.+)$", report, flags=re.MULTILINE) == REPORT_HEADINGS
    for removed in ("## 检索假设", "## 检索式", "## 论文网址", "## 数据源检索状态"):
        assert removed not in report
    assert "Paper \\| One" in report
    assert report.count("| 1 |") == 1
    assert report.count("| 2 |") == 1
    assert report.count("| 3 |") == 1
    assert "未核验" in report


def test_empty_result_uses_the_same_sections_and_generic_limitations() -> None:
    result = SearchResult(
        request=SearchRequest.with_defaults(topic="robot microscopy", current_year=2026),
        query_plan={"year_from": 2022, "year_to": 2026},
    )

    report = render_markdown(result)

    assert re.findall(r"^## (.+)$", report, flags=re.MULTILINE) == REPORT_HEADINGS
    assert "数据源覆盖范围" in report
    for source_detail in ("Crossref", "Europe PMC", "arXiv", "DBLP", "OpenAlex", "Semantic Scholar"):
        assert source_detail not in report
    for status_detail in ("成功", "失败", "跳过", "状态"):
        assert status_detail not in report


def test_table_contains_clickable_paper_and_code_links(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)

    assert "| 论文链接 | 开源代码 |" in report
    assert "[论文](https://doi.org/10.1000/one)" in report
    assert "[代码](https://github.com/example/paper-one)" in report
    assert report.count("未找到") >= 1


def test_code_link_detection_and_primary_link_excludes_code_links() -> None:
    paper = Paper(
        title="Code host fallback",
        links=[
            PaperLink(kind="repository", url="https://gitlab.com/example/project"),
            PaperLink(kind="publisher", url="https://example.org/paper"),
        ],
    )

    assert _code_url(paper) == "https://gitlab.com/example/project"
    assert _primary_paper_url(paper) == "https://example.org/paper"


def test_code_host_in_a_paper_path_is_not_treated_as_a_code_link() -> None:
    paper = Paper(
        title="Host text in path",
        links=[
            PaperLink(
                kind="publisher",
                url="https://example.org/articles/github.com-study",
            ),
            PaperLink(kind="repository", url="https://GitLab.com/example/project"),
        ],
    )

    assert _code_url(paper) == "https://GitLab.com/example/project"
    assert _primary_paper_url(paper) == "https://example.org/articles/github.com-study"


def test_csv_and_json_outputs_are_machine_readable(
    sample_result: SearchResult,
    tmp_path,
) -> None:
    csv_path = tmp_path / "report.csv"
    json_path = tmp_path / "report.json"

    write_csv(sample_result, csv_path)
    write_json(sample_result, json_path)

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert [row["序号"] for row in rows] == ["1", "2", "3"]
    assert rows[0]["论文链接"] == "https://doi.org/10.1000/one"
    assert rows[0]["开源代码"] == "https://github.com/example/paper-one"
    assert rows[2]["论文链接"] == "未找到"
    assert rows[2]["开源代码"] == "未找到"
    assert rows[2]["年份"] == "未核验"
    assert payload["request"]["topic"] == "机器人显微镜自动对焦"
    assert "source_statuses" not in payload
    assert "query_plan" in payload


def test_reporting_module_has_no_legacy_source_status_compatibility() -> None:
    reporting_source = (ROOT / "src" / "academic_paper_discovery" / "reporting.py").read_text(
        encoding="utf-8"
    )

    assert "source_statuses" not in reporting_source
