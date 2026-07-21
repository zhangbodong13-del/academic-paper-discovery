"""把检索结果渲染为中文 Markdown 报告。"""

from __future__ import annotations

from urllib.parse import urlparse

from academic_paper_discovery.models import (
    Paper,
    RecommendationTier,
    SearchResult,
)


TIER_LABELS = {
    RecommendationTier.MUST_READ: "必读",
    RecommendationTier.STRONG: "强相关",
}

CODE_HOSTS = (
    "github.com",
    "gitlab.com",
    "codeberg.org",
)


def render_markdown(result: SearchResult) -> str:
    """生成只包含必读和强相关论文的 Markdown 对比表。"""

    selected_papers = [
        paper
        for paper in result.papers
        if paper.tier
        in {
            RecommendationTier.MUST_READ,
            RecommendationTier.STRONG,
        }
    ]

    lines = [
        f"# 论文检索报告：{result.request.topic}",
        "",
        "> 本报告只检索论文元数据和公开网页链接，不下载论文正文或 PDF。",
        "",
        "## 论文对比表",
        "",
    ]

    if not selected_papers:
        lines.extend(
            [
                "本次检索未筛选出必读或强相关论文。",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "| 序号 | 分组 | 论文 | 作者 | 年份 | 期刊/会议 | 影响力指标 | 得分 | 创新点 | 论文链接 | 开源代码 |",
            "| ---: | --- | --- | --- | ---: | --- | --- | ---: | --- | --- | --- |",
        ]
    )

    for number, paper in enumerate(selected_papers, start=1):
        authors = "、".join(paper.authors) if paper.authors else "未核验"
        year = str(paper.year) if paper.year is not None else "未核验"
        venue = paper.venue or "未核验"
        tier_label = TIER_LABELS.get(paper.tier, "未分组")
        impact_metric = paper.impact_metric or "未核验"
        innovation = paper.innovation or "未核验"

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
                    _escape_table(impact_metric),
                    f"{paper.score:.3f}",
                    _escape_table(innovation),
                    _markdown_link(
                        "论文",
                        _primary_paper_url(paper),
                    ),
                    _markdown_link(
                        "代码",
                        _code_url(paper),
                    ),
                ]
            )
            + " |"
        )

    lines.append("")
    return "\n".join(lines)


def _code_url(paper: Paper) -> str | None:
    """返回第一条代码仓库链接。"""

    for link in paper.links:
        if _is_code_link(link.kind, link.url):
            return link.url

    return None


def _primary_paper_url(paper: Paper) -> str | None:
    """优先返回 DOI，否则返回第一条非代码链接。"""

    if paper.doi:
        return f"https://doi.org/{paper.doi}"

    for link in paper.links:
        if not _is_code_link(link.kind, link.url):
            return link.url

    return None


def _markdown_link(
    label: str,
    url: str | None,
) -> str:
    """生成 Markdown 链接，缺失时写未找到。"""

    if not url:
        return "未找到"

    return f"[{label}]({url})"


def _is_code_link(
    kind: str | None,
    url: str,
) -> bool:
    """判断链接是否指向代码仓库。"""

    if "code" in (kind or "").casefold():
        return True

    hostname = urlparse(url).hostname
    if hostname is None:
        return False

    normalized_hostname = hostname.casefold()

    return any(
        normalized_hostname == host
        or normalized_hostname.endswith(f".{host}")
        for host in CODE_HOSTS
    )


def _escape_table(value: str) -> str:
    """转义会破坏 Markdown 表格结构的字符。"""

    return (
        value.replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )