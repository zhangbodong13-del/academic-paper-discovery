"""所有论文来源遵循的统一接口。"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from academic_paper_discovery.models import Paper, SearchRequest
from academic_paper_discovery.query_plan import QueryPlan


class AdapterResult(BaseModel):
    """单一来源返回的论文元数据。"""

    model_config = ConfigDict(extra="forbid")

    papers: list[Paper] = Field(default_factory=list)


class PaperSource(Protocol):
    """论文元数据来源协议。"""

    name: str

    def search(self, plan: QueryPlan, request: SearchRequest) -> AdapterResult:
        """检索论文元数据，不下载论文正文。"""

