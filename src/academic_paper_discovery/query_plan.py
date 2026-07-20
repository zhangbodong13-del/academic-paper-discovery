"""把 Codex 生成的检索表达整理为可审计查询计划。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from academic_paper_discovery.models import SearchRequest


class QueryPlan(BaseModel):
    """最终报告中可以直接展示的查询计划。"""

    model_config = ConfigDict(extra="forbid")

    original_topic: str
    queries: list[str] = Field(default_factory=list)
    venue_queries: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    year_from: int
    year_to: int
    assumptions: list[str] = Field(default_factory=list)


def _stable_unique(values: list[str]) -> list[str]:
    """规范空白并按首次出现顺序做不区分大小写的去重。"""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def build_query_plan(request: SearchRequest) -> QueryPlan:
    """从已校验请求构建确定性的查询计划。"""

    assumptions: list[str] = []
    if request.year_range_was_defaulted:
        assumptions.append(f"默认年份范围：{request.year_from}-{request.year_to}")

    return QueryPlan(
        original_topic=request.topic,
        queries=_stable_unique([request.topic, *request.expanded_queries]),
        venue_queries=_stable_unique(request.target_venues),
        exclusions=_stable_unique(request.exclusions),
        year_from=request.year_from,
        year_to=request.year_to,
        assumptions=assumptions,
    )
