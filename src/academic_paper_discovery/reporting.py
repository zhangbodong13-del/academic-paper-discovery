"""把检索结果渲染为中文 Markdown、CSV 和 JSON。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

from academic_paper_discovery.models import Paper, RecommendationTier, SearchResult


TIER_LABELS = {
    RecommendationTier.MUST_READ: "必读",
    RecommendationTier.STRONG: "强相关",
    RecommendationTier.EXPLORATORY: "拓展阅读",
}
CODE_HOSTS = ("github.com", "gitlab.com", "codeberg.org")


def render_markdown(result: SearchResult) -> str:
    """生成包含分层推荐和链接对比表的中文 Markdown 报告。"""

    lines = [
        f"# 论文检索报告：{result.request.topic}",
        "",
        "> 本报告只检索论文元数据和公开网页链接，不下载论文正文或 PDF。",
    ]
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
            "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 得分 | 推荐理由 | 论文链接 | 开源代码 |",
            "| ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- |",
        ]
    )
    for number, paper in numbered:
        authors = "、".join(paper.authors) if paper.authors else "未核验"
        year = str(paper.year) if paper.year is not None else "未核验"
        venue = paper.venue or "未核验"
        tier_label = TIER_LABELS.get(paper.tier, "未分组")
        reason = paper.why_read or "未核验"
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
                    _markdown_link("论文", _primary_paper_url(paper)),
                    _markdown_link("代码", _code_url(paper)),
                ]
            )
            + " |"
        )

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
        "论文链接",
        "开源代码",
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
                    "论文链接": _primary_paper_url(paper) or "未找到",
                    "开源代码": _code_url(paper) or "未找到",
                }
            )
    return output_path


def write_json(result: SearchResult, path: str | Path) -> Path:
    """写出保留检索计划的 UTF-8 JSON。"""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _code_url(paper: Paper) -> str | None:
    """返回第一条被标记为代码或指向已知代码托管站的链接。"""

    for link in paper.links:
        if _is_code_link(link.kind, link.url):
            return link.url
    return None


def _primary_paper_url(paper: Paper) -> str | None:
    """优先返回 DOI；否则返回第一条非代码链接。"""

    if paper.doi:
        return f"https://doi.org/{paper.doi}"
    for link in paper.links:
        if not _is_code_link(link.kind, link.url):
            return link.url
    return None


def _markdown_link(label: str, url: str | None) -> str:
    """将 URL 渲染为可点击 Markdown，缺失时明确标记。"""

    return f"[{label}]({url})" if url else "未找到"


def _is_code_link(kind: str | None, url: str) -> bool:
    if "code" in (kind or "").casefold():
        return True
    hostname = urlparse(url).hostname
    if hostname is None:
        return False
    return any(
        hostname.casefold() == host or hostname.casefold().endswith(f".{host}")
        for host in CODE_HOSTS
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
