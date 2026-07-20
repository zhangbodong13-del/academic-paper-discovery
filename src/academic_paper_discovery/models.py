"""检索管线共享的数据模型。"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecommendationTier(StrEnum):
    """论文推荐层级的稳定内部值。"""

    MUST_READ = "must-read"
    STRONG = "strong"
    EXPLORATORY = "exploratory"


class PaperLink(BaseModel):
    """论文元数据中发现的网址；不会自动访问或下载目标内容。"""

    model_config = ConfigDict(extra="forbid")

    kind: str = "landing"
    url: str
    source: str = ""
    verified: bool = False

    @field_validator("url")
    @classmethod
    def validate_web_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("网址必须使用 http 或 https")
        return cleaned


class SearchRequest(BaseModel):
    """一次论文检索的用户约束。"""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    expanded_queries: list[str] = Field(default_factory=list)
    year_from: int = Field(ge=1800, le=2200)
    year_to: int = Field(ge=1800, le=2200)
    year_range_was_defaulted: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    target_venues: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    prefer_reviews: bool = False
    prefer_code: bool = False
    high_relevance_only: bool = False
    include_cross_domain: bool = True
    source_limit: int = Field(default=50, ge=1, le=200)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("研究主题不能为空")
        return cleaned

    @model_validator(mode="after")
    def validate_year_range(self) -> SearchRequest:
        if self.year_from > self.year_to:
            raise ValueError("起始年份不能晚于结束年份")
        return self

    @classmethod
    def with_defaults(
        cls,
        *,
        topic: str,
        current_year: int,
        **overrides: object,
    ) -> SearchRequest:
        """创建请求，并显式记录是否使用默认五年窗口。"""

        values = dict(overrides)
        supplied_from = values.pop("year_from", None)
        supplied_to = values.pop("year_to", None)
        if supplied_from is None and supplied_to is None:
            year_from = current_year - 4
            year_to = current_year
            was_defaulted = True
        elif supplied_from is None or supplied_to is None:
            raise ValueError("起始年份和结束年份必须同时提供")
        else:
            year_from = supplied_from
            year_to = supplied_to
            was_defaulted = False

        return cls(
            topic=topic,
            year_from=year_from,
            year_to=year_to,
            year_range_was_defaulted=was_defaulted,
            **values,
        )


class Paper(BaseModel):
    """跨数据源统一后的论文元数据。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1800, le=2200)
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    citation_count: int | None = Field(default=None, ge=0)
    publication_type: str | None = None
    is_formal: bool = False
    links: list[PaperLink] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)
    raw_ids: dict[str, str] = Field(default_factory=dict)
    score: float = 0.0
    score_components: dict[str, float] = Field(default_factory=dict)
    tier: RecommendationTier | None = None
    why_read: str = ""
    warnings: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("论文标题不能为空")
        return cleaned

    @field_validator("doi", mode="before")
    @classmethod
    def normalize_doi(cls, value: object) -> object:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        cleaned = re.sub(
            r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
            "",
            cleaned,
        )
        return cleaned or None


class SearchResult(BaseModel):
    """完整检索结果。"""

    model_config = ConfigDict(extra="forbid")

    request: SearchRequest
    papers: list[Paper] = Field(default_factory=list)
    query_plan: dict[str, object] = Field(default_factory=dict)
    total_candidates: int = Field(default=0, ge=0)
