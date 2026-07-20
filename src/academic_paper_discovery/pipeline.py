"""多来源论文元数据检索的容错编排。"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from academic_paper_discovery.adapters.base import AdapterResult, PaperSource
from academic_paper_discovery.deduplication import deduplicate
from academic_paper_discovery.models import (
    RecommendationTier,
    SearchRequest,
    SearchResult,
    SourceStatus,
)
from academic_paper_discovery.query_plan import QueryPlan, build_query_plan
from academic_paper_discovery.ranking import rank_papers


class SearchPipeline:
    """并发调用数据源，并以稳定顺序汇总、去重和排序。"""

    def __init__(
        self,
        sources: list[PaperSource],
        *,
        current_year: int,
        total_candidate_limit: int = 500,
        max_workers: int = 4,
        fuzzy_threshold: int = 92,
        low_confidence_threshold: int = 86,
    ) -> None:
        if total_candidate_limit < 1:
            raise ValueError("候选论文总上限必须大于零")
        if max_workers < 1:
            raise ValueError("并发数必须大于零")
        self.sources = sources
        self.current_year = current_year
        self.total_candidate_limit = total_candidate_limit
        self.max_workers = max_workers
        self.fuzzy_threshold = fuzzy_threshold
        self.low_confidence_threshold = low_confidence_threshold

    def run(self, request: SearchRequest) -> SearchResult:
        """执行检索；单个来源失败不会中断整次任务。"""

        plan = build_query_plan(request)
        adapter_results = self._search_sources(plan, request)

        candidates = []
        for adapter_result in adapter_results:
            remaining = self.total_candidate_limit - len(candidates)
            if remaining <= 0:
                break
            candidates.extend(adapter_result.papers[: min(request.source_limit, remaining)])

        merged = deduplicate(
            candidates,
            fuzzy_threshold=self.fuzzy_threshold,
            low_confidence_threshold=self.low_confidence_threshold,
        )
        ranked = rank_papers(
            merged,
            request,
            plan,
            current_year=self.current_year,
        )
        if request.high_relevance_only:
            ranked = [
                paper
                for paper in ranked
                if paper.tier is not RecommendationTier.EXPLORATORY
            ]

        return SearchResult(
            request=request,
            papers=ranked[: request.limit],
            source_statuses=[result.status for result in adapter_results],
            query_plan=plan.model_dump(mode="json"),
            total_candidates=len(candidates),
        )

    def _search_sources(
        self,
        plan: QueryPlan,
        request: SearchRequest,
    ) -> list[AdapterResult]:
        if not self.sources:
            return []

        results: list[AdapterResult | None] = [None] * len(self.sources)
        worker_count = min(self.max_workers, len(self.sources))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures: dict[Future[AdapterResult], int] = {
                executor.submit(source.search, plan, request): index
                for index, source in enumerate(self.sources)
            }
            for future in as_completed(futures):
                index = futures[future]
                source = self.sources[index]
                try:
                    results[index] = future.result()
                except Exception as error:  # 每个外部来源都有独立故障边界。
                    results[index] = AdapterResult(
                        status=SourceStatus(
                            source=source.name,
                            state="failed",
                            message=f"数据源运行失败：{error}",
                        )
                    )

        return [result for result in results if result is not None]
