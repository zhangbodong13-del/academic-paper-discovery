from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TABLE_HEADER = (
    "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | "
    "影响力指标 | 得分 | 创新点 | 论文链接 | 开源代码 |"
)

REMOVED_REPORT_SECTIONS = (
    "## 必读",
    "## 强相关",
    "## 拓展阅读",
    "## 局限与下一步",
    "## 数据源检索状态",
    "## 论文网址",
)


def test_readme_describes_the_skill_and_current_output() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "# Academic Paper Discovery" in readme
    assert "多来源学术论文检索与筛选 Skill" in readme
    assert "## 安装 Skill" in readme
    assert "## 使用实例" in readme
    assert "$academic-paper-discovery" in readme
    assert "不下载论文正文或 PDF" in readme
    assert EXPECTED_TABLE_HEADER in readme

    for section in REMOVED_REPORT_SECTIONS:
        assert section not in readme


def test_skill_frontmatter_and_body_match_current_contract() -> None:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter_text, body = content.split("---", maxsplit=2)
    frontmatter = yaml.safe_load(frontmatter_text)

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "academic-paper-discovery"

    description = frontmatter["description"]
    assert description.startswith("Use when")

    for trigger in (
        "literature search",
        "paper recommendations",
        "venue-focused",
        "research landscape",
        "structured comparison table",
    ):
        assert trigger in description

    assert "多来源论文检索" in body
    assert "不下载论文正文或 PDF" in body
    assert "report.md" in body
    assert "## 论文对比表" in body
    assert "只输出以下两类论文" in body
    assert "必读" in body
    assert "强相关" in body

    for section in REMOVED_REPORT_SECTIONS:
        assert section not in body


def test_output_contract_matches_single_table_report() -> None:
    output_contract = (
        ROOT / "references" / "output-contract.md"
    ).read_text(encoding="utf-8")

    assert "最终只生成一个 `report.md`" in output_contract
    assert "## 论文对比表" in output_contract
    assert "影响力指标" in output_contract
    assert "创新点" in output_contract
    assert "[论文](URL)" in output_contract
    assert "[代码](URL)" in output_contract
    assert "只输出“必读”和“强相关”论文" in output_contract

    for section in REMOVED_REPORT_SECTIONS:
        assert section not in output_contract


def test_report_template_contains_only_comparison_table() -> None:
    template = (
        ROOT / "assets" / "report-template.md"
    ).read_text(encoding="utf-8")

    assert template.count("## 论文对比表") == 1
    assert EXPECTED_TABLE_HEADER in template
    assert "不下载论文正文或 PDF" in template

    for section in REMOVED_REPORT_SECTIONS:
        assert section not in template


def test_development_doc_matches_markdown_only_output() -> None:
    development = (
        ROOT / "docs" / "DEVELOPMENT.md"
    ).read_text(encoding="utf-8")

    assert "report.md" in development
    assert "影响力指标" in development
    assert "--offline-fixture" in development
    assert "report.csv" not in development
    assert "report.json" not in development


def test_source_policy_keeps_failure_isolation() -> None:
    source_policy = (
        ROOT / "references" / "source-policy.md"
    ).read_text(encoding="utf-8")

    assert "任何来源失败都不应阻止已成功来源进入去重和排序" in source_policy


def test_agent_interface_is_chinese() -> None:
    config = yaml.safe_load(
        (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )

    assert config["interface"]["display_name"] == "学术论文发现"
    assert "论文" in config["interface"]["short_description"]
    assert "$academic-paper-discovery" in config["interface"]["default_prompt"]