"""可解释、时间友好的论文相关性排序。"""

from __future__ import annotations

import math
import re
import unicodedata

from academic_paper_discovery.models import (
    Paper,
    RecommendationTier,
    SearchRequest,
)
from academic_paper_discovery.query_plan import QueryPlan


DEFAULT_WEIGHTS = {
    "title_relevance": 0.35,
    "abstract_relevance": 0.20,
    "target_venue": 0.10,
    "multi_source": 0.08,
    "formal_version": 0.05,
    "code_available": 0.05,
    "recency": 0.04,
    "citation_age_normalized": 0.13,
}


def rank_papers(
    papers: list[Paper],
    request: SearchRequest,
    plan: QueryPlan,
    *,
    current_year: int,
    weights: dict[str, float] | None = None,
    must_read_threshold: float = 0.75,
    strong_threshold: float = 0.55,
) -> list[Paper]:
    """计算透明分项得分并返回稳定排序。"""

    active_weights = weights or DEFAULT_WEIGHTS
    query_token_sets = [_tokens(query) for query in plan.queries]
    target_venues = {_normalize_text(value) for value in request.target_venues}
    ranked: list[Paper] = []

    for original in papers:
        paper = original.model_copy(deep=True)
        components = {
            "title_relevance": _best_coverage(paper.title, query_token_sets),
            "abstract_relevance": _best_coverage(
                paper.abstract or "",
                query_token_sets,
            ),
            "target_venue": float(
                bool(paper.venue)
                and _normalize_text(paper.venue or "") in target_venues
            ),
            "multi_source": min(len(set(paper.source_names)) / 2.0, 1.0),
            "formal_version": float(paper.is_formal),
            "code_available": float(
                any(link.kind.casefold() in {"code", "project"} for link in paper.links)
            ),
            "recency": _recency(paper.year, current_year),
            "citation_age_normalized": _citation_impact(
                paper.citation_count,
                paper.year,
                current_year,
            ),
        }
        score = sum(
            components[name] * active_weights.get(name, 0.0)
            for name in components
        )
        paper.score_components = {name: round(value, 6) for name, value in components.items()}
        paper.score = round(score, 6)
        paper.tier = _tier(score, must_read_threshold, strong_threshold)
        paper.why_read = _why_read(components)
        ranked.append(paper)

    return sorted(ranked, key=lambda paper: (-paper.score, _normalize_text(paper.title)))


def _best_coverage(text: str, query_token_sets: list[set[str]]) -> float:
    text_tokens = _tokens(text)
    if not text_tokens:
        return 0.0
    coverages = [
        len(text_tokens & query_tokens) / len(query_tokens)
        for query_tokens in query_token_sets
        if query_tokens
    ]
    return max(coverages, default=0.0)


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized))


def _normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _recency(year: int | None, current_year: int) -> float:
    if year is None:
        return 0.0
    age = max(0, current_year - year)
    return max(0.0, 1.0 - age / 10.0)


def _citation_impact(
    citations: int | None,
    year: int | None,
    current_year: int,
) -> float:
    if citations is None or citations <= 0:
        return 0.0
    age = max(0, current_year - year) if year is not None else 5
    citations_per_year = citations / (age + 1)
    return min(math.log1p(citations_per_year) / math.log1p(100), 1.0)


def _tier(
    score: float,
    must_read_threshold: float,
    strong_threshold: float,
) -> RecommendationTier:
    if score >= must_read_threshold:
        return RecommendationTier.MUST_READ
    if score >= strong_threshold:
        return RecommendationTier.STRONG
    return RecommendationTier.EXPLORATORY


def _why_read(components: dict[str, float]) -> str:
    reasons: list[str] = []
    if components["title_relevance"] >= 0.6:
        reasons.append("标题与研究问题高度匹配")
    if components["abstract_relevance"] >= 0.5:
        reasons.append("摘要覆盖核心概念")
    if components["target_venue"]:
        reasons.append("来自目标期刊或会议")
    if components["multi_source"] >= 1.0:
        reasons.append("得到多个来源交叉验证")
    if components["formal_version"]:
        reasons.append("已有正式发表版本")
    if components["code_available"]:
        reasons.append("发现代码或项目页")
    return "；".join(reasons) if reasons else "与查询存在有限关联，建议核验摘要"
