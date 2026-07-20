import csv
import json

import pytest

from academic_paper_discovery.models import (
    Paper,
    PaperLink,
    RecommendationTier,
    SearchRequest,
    SearchResult,
    SourceStatus,
)
from academic_paper_discovery.reporting import render_markdown, write_csv, write_json


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
        source_statuses=[
            SourceStatus(source="crossref", state="success", result_count=10),
            SourceStatus(
                source="openalex",
                state="skipped",
                message="未配置 API Key",
            ),
            SourceStatus(
                source="arxiv",
                state="failed",
                message="请求超时",
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


def test_markdown_follows_b_plus_c_contract(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)

    headings = [
        "## 检索假设",
        "## 检索式",
        "## 必读",
        "## 强相关",
        "## 拓展阅读",
        "## 论文对比表",
        "## 论文网址",
        "## 数据源检索状态",
        "## 局限与下一步",
    ]
    positions = [report.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert report.index("| 序号 |") < report.index("## 论文网址")
    assert "Paper \\| One" in report
    assert report.count("| 1 |") == 1
    assert report.count("| 2 |") == 1
    assert report.count("| 3 |") == 1
    assert "未核验" in report
    assert "未找到" in report


def test_urls_follow_table_with_matching_numbers(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)
    url_section = report.split("## 论文网址", maxsplit=1)[1].split(
        "## 数据源检索状态", maxsplit=1
    )[0]

    assert "1. **Paper | One**" in url_section
    assert "2. **Paper Two**" in url_section
    assert "3. **Paper Three**" in url_section
    assert "https://example.org/paper/one?full=true" in url_section
    assert "https://github.com/example/paper-one" in url_section
    assert "https://doi.org/10.1000/two" in url_section
    assert url_section.index("1. **Paper | One**") < url_section.index("2. **Paper Two**")
    assert url_section.index("2. **Paper Two**") < url_section.index("3. **Paper Three**")


def test_source_states_are_reported_as_actual_outcomes(sample_result: SearchResult) -> None:
    report = render_markdown(sample_result)

    assert "crossref：成功（10 篇）" in report
    assert "openalex：跳过（未配置 API Key）" in report
    assert "arxiv：失败（请求超时）" in report


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
    assert rows[0]["完整网址"].startswith("https://doi.org/10.1000/one")
    assert rows[2]["年份"] == "未核验"
    assert payload["request"]["topic"] == "机器人显微镜自动对焦"
    assert payload["source_statuses"][2]["state"] == "failed"
