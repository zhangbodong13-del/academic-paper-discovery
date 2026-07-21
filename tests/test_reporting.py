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
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_HEADINGS = ["论文对比表"]


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
                abstract=(
                    "This work introduces a disparity-aware autofocus method "
                    "for robotic microscopy."
                ),
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
                impact_metric="IF 25.8（2025 JCR）",
                innovation="提出面向机器人显微镜的视差感知自动对焦方法。",
            ),
            Paper(
                title="Paper Two",
                authors=["Grace Hopper"],
                year=2024,
                venue="CVPR",
                abstract=(
                    "The method combines stereo disparity and image blur "
                    "for robust focus estimation."
                ),
                doi="10.1000/two",
                source_names=["dblp"],
                score=0.66,
                tier=RecommendationTier.STRONG,
                why_read="提供互补方法",
                impact_metric="CCF A（2022版）/ CORE A*（2023版）",
                innovation="融合双目视差和图像模糊信息进行焦点估计。",
            ),
            Paper(
                title="Paper Three",
                source_names=["dblp"],
                score=0.3,
                tier=RecommendationTier.EXPLORATORY,
                why_read="用于拓展阅读",
                impact_metric="未核验",
                innovation="未核验",
            ),
        ],
        query_plan={
            "original_topic": "机器人显微镜自动对焦",
            "queries": [
                "机器人显微镜自动对焦",
                "robot microscope autofocus",
            ],
            "venue_queries": [],
            "exclusions": [],
            "year_from": 2022,
            "year_to": 2026,
            "assumptions": ["默认年份范围：2022-2026"],
        },
        total_candidates=23,
    )


def test_markdown_only_contains_comparison_table(
    sample_result: SearchResult,
) -> None:
    report = render_markdown(sample_result)

    assert re.findall(r"^## (.+)$", report, flags=re.MULTILINE) == REPORT_HEADINGS

    for removed_heading in (
        "## 必读",
        "## 强相关",
        "## 拓展阅读",
        "## 局限与下一步",
        "## 检索假设",
        "## 检索式",
        "## 论文网址",
        "## 数据源检索状态",
    ):
        assert removed_heading not in report


def test_table_only_contains_must_read_and_strong_papers(
    sample_result: SearchResult,
) -> None:
    report = render_markdown(sample_result)

    assert "Paper \\| One" in report
    assert "Paper Two" in report
    assert "Paper Three" not in report

    assert report.count("| 1 |") == 1
    assert report.count("| 2 |") == 1
    assert "| 3 |" not in report

    assert "| 必读 |" in report
    assert "| 强相关 |" in report
    assert "| 拓展阅读 |" not in report


def test_table_has_impact_metric_score_and_innovation_columns(
    sample_result: SearchResult,
) -> None:
    report = render_markdown(sample_result)

    assert (
        "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | "
        "影响力指标 | 得分 | 创新点 | 论文链接 | 开源代码 |"
    ) in report

    assert "推荐理由" not in report
    assert "IF 25.8（2025 JCR）" in report
    assert "CCF A（2022版）/ CORE A*（2023版）" in report
    assert "提出面向机器人显微镜的视差感知自动对焦方法。" in report
    assert "融合双目视差和图像模糊信息进行焦点估计。" in report


def test_empty_result_has_only_comparison_table_section() -> None:
    result = SearchResult(
        request=SearchRequest.with_defaults(
            topic="robot microscopy",
            current_year=2026,
        ),
        query_plan={"year_from": 2022, "year_to": 2026},
    )

    report = render_markdown(result)

    assert re.findall(r"^## (.+)$", report, flags=re.MULTILINE) == REPORT_HEADINGS
    assert "本次检索未筛选出必读或强相关论文。" in report
    assert "局限与下一步" not in report


def test_table_contains_clickable_paper_and_code_links(
    sample_result: SearchResult,
) -> None:
    report = render_markdown(sample_result)

    assert "| 论文链接 | 开源代码 |" in report
    assert "[论文](https://doi.org/10.1000/one)" in report
    assert "[代码](https://github.com/example/paper-one)" in report
    assert report.count("未找到") >= 1


def test_code_link_detection_and_primary_link_excludes_code_links() -> None:
    paper = Paper(
        title="Code host fallback",
        links=[
            PaperLink(
                kind="repository",
                url="https://gitlab.com/example/project",
            ),
            PaperLink(
                kind="publisher",
                url="https://example.org/paper",
            ),
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
            PaperLink(
                kind="repository",
                url="https://GitLab.com/example/project",
            ),
        ],
    )

    assert _code_url(paper) == "https://GitLab.com/example/project"
    assert _primary_paper_url(paper) == "https://example.org/articles/github.com-study"


def test_reporting_module_has_no_csv_or_json_writers() -> None:
    reporting_source = (
        ROOT
        / "src"
        / "academic_paper_discovery"
        / "reporting.py"
    ).read_text(encoding="utf-8")

    assert "def write_csv" not in reporting_source
    assert "def write_json" not in reporting_source