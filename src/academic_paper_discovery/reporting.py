"""把检索结果渲染为中文 Markdown、CSV 和 JSON。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from academic_paper_discovery.models import (
    Paper,
    RecommendationTier,
    SearchResult,
    SourceStatus,
)


TIER_LABELS = {
    RecommendationTier.MUST_READ: "必读",
    RecommendationTier.STRONG: "强相关",
    RecommendationTier.EXPLORATORY: "拓展阅读",
}
STATE_LABELS = {
    "success": "成功",
    "failed": "失败",
    "skipped": "跳过",
}


def render_markdown(result: SearchResult) -> str:
    """按 B+C 契约生成可审计的中文 Markdown 报告。"""

    lines = [
        f"# 论文检索报告：{result.request.topic}",
        "",
        "> 本报告只检索论文元数据和公开网页链接，不下载论文正文或 PDF。",
        "",
        "## 检索假设",
        "",
    ]
    assumptions = _string_list(result.query_plan.get("assumptions"))
    if assumptions:
        lines.extend(f"- {value}" for value in assumptions)
    else:
        lines.append("- 未使用额外假设；年份范围由用户明确提供。")

    lines.extend(["", "## 检索式", ""])
    queries = _string_list(result.query_plan.get("queries"))
    lines.extend(f"- `{value}`" for value in queries)
    if not queries:
        lines.append("- 未找到可展示的检索式")
    venue_queries = _string_list(result.query_plan.get("venue_queries"))
    if venue_queries:
        lines.append(f"- 目标期刊/会议：{', '.join(venue_queries)}")
    exclusions = _string_list(result.query_plan.get("exclusions"))
    if exclusions:
        lines.append(f"- 排除词：{', '.join(exclusions)}")

    numbered = list(enumerate(result.papers, start=1))
    for tier in (
        RecommendationTier.MUST_READ,
        RecommendationTier.STRONG,
        RecommendationTier.EXPLORATORY,
    ):
        lines.extend(["", f"## {TIER_LABELS[tier]}", ""])
        tier_papers = [(number, paper) for number, paper in numbered if paper.tier == tier]
        if not tier_papers:
            lines.append("本次检索未筛选出该层级论文。")
            continue
        for number, paper in tier_papers:
            lines.append(
                f"{number}. **{paper.title}** — {paper.why_read or '推荐理由未核验'}"
            )

    lines.extend(
        [
            "",
            "## 论文对比表",
            "",
            "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 得分 | 推荐理由 | 访问 |",
            "| ---: | --- | --- | --- | ---: | --- | ---: | --- | --- |",
        ]
    )
    for number, paper in numbered:
        authors = "、".join(paper.authors) if paper.authors else "未核验"
        year = str(paper.year) if paper.year is not None else "未核验"
        venue = paper.venue or "未核验"
        tier_label = TIER_LABELS.get(paper.tier, "未分组")
        reason = paper.why_read or "未核验"
        primary_url = _paper_urls(paper)[0][1] if _paper_urls(paper) else None
        access = f"[访问]({primary_url})" if primary_url else "未找到"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(number),
                    _escape_table(tier_label),
                    _escape_table(paper.title),
                    _escape_table(authors),
                    year,
                    _escape_table(venue),
                    f"{paper.score:.3f}",
                    _escape_table(reason),
                    access,
                ]
            )
            + " |"
        )

    lines.extend(["", "## 论文网址", ""])
    for number, paper in numbered:
        lines.append(f"{number}. **{paper.title}**")
        urls = _paper_urls(paper)
        if not urls:
            lines.append("   - 未找到")
        else:
            for label, url, verified in urls:
                verification = "" if verified else "（未核验）"
                lines.append(f"   - {label}：{url}{verification}")

    lines.extend(["", "## 数据源检索状态", ""])
    if result.source_statuses:
        lines.extend(f"- {_render_status(status)}" for status in result.source_statuses)
    else:
        lines.append("- 未配置数据源")
    lines.append(f"- 进入排序前的候选论文数：{result.total_candidates}")

    lines.extend(
        [
            "",
            "## 局限与下一步",
            "",
            "- 结果受检索式、年份、数据源覆盖范围和服务可用性影响，不代表穷尽性检索。",
            "- 未核验字段和网址应在引用前回到 DOI 或出版方页面人工确认。",
            "- 如结果不足，可补充同义词、作者、目标期刊/会议或调整年份范围后再次检索。",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv(result: SearchResult, path: str | Path) -> Path:
    """写出便于表格软件读取的 UTF-8 BOM CSV。"""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "序号",
        "分组",
        "标题",
        "作者",
        "年份",
        "期刊/会议",
        "DOI",
        "得分",
        "推荐理由",
        "数据源",
        "完整网址",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for number, paper in enumerate(result.papers, start=1):
            writer.writerow(
                {
                    "序号": number,
                    "分组": TIER_LABELS.get(paper.tier, "未分组"),
                    "标题": paper.title,
                    "作者": "；".join(paper.authors) if paper.authors else "未核验",
                    "年份": paper.year if paper.year is not None else "未核验",
                    "期刊/会议": paper.venue or "未核验",
                    "DOI": paper.doi or "未核验",
                    "得分": f"{paper.score:.6f}",
                    "推荐理由": paper.why_read or "未核验",
                    "数据源": "；".join(paper.source_names) or "未核验",
                    "完整网址": "；".join(url for _, url, _ in _paper_urls(paper))
                    or "未找到",
                }
            )
    return output_path


def write_json(result: SearchResult, path: str | Path) -> Path:
    """写出保留完整可审计字段的 UTF-8 JSON。"""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump(mode="json")
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _paper_urls(paper: Paper) -> list[tuple[str, str, bool]]:
    urls: list[tuple[str, str, bool]] = []
    seen: set[str] = set()
    if paper.doi:
        doi_url = f"https://doi.org/{paper.doi}"
        urls.append(("DOI", doi_url, True))
        seen.add(doi_url.casefold())
    for link in paper.links:
        key = link.url.casefold()
        if key in seen:
            continue
        seen.add(key)
        label = link.kind or link.source or "网页"
        urls.append((label, link.url, link.verified))
    return urls


def _render_status(status: SourceStatus) -> str:
    label = STATE_LABELS[status.state]
    if status.state == "success":
        details = f"{status.result_count} 篇"
        if status.message:
            details += f"；{status.message}"
    else:
        details = status.message or "未提供原因"
    return f"{status.source}：{label}（{details}）"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
