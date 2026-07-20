from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


APPROVED_PROMPT = """使用 $academic-paper-discovery，围绕“研究主题”进行多来源论文检索。

要求：
- 年份：未指定则明确说明默认范围
- 数量：20 篇
- 优先来源：Nature、Science、相关子刊及本领域重要期刊和会议
- 输出：必读、强相关、拓展阅读
- 同时生成论文对比表
- 将完整论文网址按表格序号列在表格后面
- 说明实际检索成功和失败的数据源"""


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


def test_agent_interface_is_chinese() -> None:
    config = yaml.safe_load((ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    assert config["interface"]["display_name"] == "学术论文发现"
    assert "论文" in config["interface"]["short_description"]
    assert "$academic-paper-discovery" in config["interface"]["default_prompt"]
