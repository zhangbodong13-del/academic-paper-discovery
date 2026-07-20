from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REMOVED_REPORT_MARKERS = ("检索假设", "检索式", "论文网址", "数据源检索状态")


APPROVED_PROMPT = """使用 $academic-paper-discovery，围绕“研究主题”进行多来源论文检索。

要求：
- 年份：未指定则明确说明默认范围
- 数量：20 篇
- 优先来源：Nature、Science、相关子刊及本领域重要期刊和会议
- 输出：必读、强相关、拓展阅读
- 同时生成论文对比表
- 在表格中提供可点击的论文和开源代码链接"""


def test_readme_contains_approved_prompt_and_no_download_policy() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    development = (ROOT / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")

    assert APPROVED_PROMPT in readme
    assert "不下载论文正文或 PDF" in readme
    assert "## 这个 Skill 能做什么" in readme
    assert "## 最简单的使用方法" in readme
    assert "如果你只是使用者，看到这里就够了" in readme
    assert "D:\\academic-paper-discovery" in development
    assert "--offline-fixture" in development
    assert "数据源检索状态" not in readme
    assert "论文网址" not in readme
    assert (
        "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊或会议 | 得分 | 推荐理由 | 论文链接 | 开源代码 |"
        in readme
    )


def test_skill_frontmatter_and_body_are_ready_for_users() -> None:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter_text, body = content.split("---", maxsplit=2)
    frontmatter = yaml.safe_load(frontmatter_text)

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == "academic-paper-discovery"
    description = frontmatter["description"]
    assert description.startswith("Use when")
    for trigger in (
        "literature search",
        "must-read",
        "venue-focused",
        "research landscape",
        "structured paper table",
    ):
        assert trigger in description
    assert "多来源论文检索" in body
    assert "不下载论文正文或 PDF" in body
    assert "必读、强相关、拓展阅读" in body
    assert "论文网址必须紧跟对比表" not in body
    assert "逐项报告本次运行中真实“成功、失败、跳过”的数据源及原因" not in body


def test_output_contract_uses_clickable_links_without_removed_sections() -> None:
    output_contract = (ROOT / "references" / "output-contract.md").read_text(
        encoding="utf-8"
    )
    report_template = (ROOT / "assets" / "report-template.md").read_text(
        encoding="utf-8"
    )

    for required in ("论文链接", "开源代码", "[论文](URL)", "[代码](URL)"):
        assert required in output_contract

    headings = ["必读", "强相关", "拓展阅读", "论文对比表", "局限与下一步"]
    assert [report_template.index(f"## {heading}") for heading in headings] == sorted(
        report_template.index(f"## {heading}") for heading in headings
    )
    for removed in (f"## {section}" for section in REMOVED_REPORT_MARKERS):
        assert removed not in report_template

    for marker in REMOVED_REPORT_MARKERS:
        assert marker not in output_contract
        assert f"## {marker}" not in output_contract
    assert "报告只生成上述五个固定章节。" in output_contract


def test_skill_contains_only_the_approved_report_sections() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    output_section = skill.split("### 5. 输出中文报告", maxsplit=1)[1].split(
        "## 交付前检查", maxsplit=1
    )[0]

    for marker in REMOVED_REPORT_MARKERS:
        assert marker not in output_section
        assert f"## {marker}" not in output_section
    assert "报告只生成上述五个固定章节。" in output_section


def test_source_policy_keeps_failure_isolation_without_status_reporting() -> None:
    source_policy = (ROOT / "references" / "source-policy.md").read_text(encoding="utf-8")

    assert "任何来源失败都不应阻止已成功来源进入去重和排序" in source_policy
    assert "状态" not in source_policy
    for removed in ("## 状态定义", "成功：", "失败：", "跳过：", "报告必须保留失败原因"):
        assert removed not in source_policy


def test_agent_interface_is_chinese() -> None:
    config = yaml.safe_load((ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    assert config["interface"]["display_name"] == "学术论文发现"
    assert "论文" in config["interface"]["short_description"]
    assert "$academic-paper-discovery" in config["interface"]["default_prompt"]
