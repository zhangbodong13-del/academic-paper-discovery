"""多来源论文元数据检索的容错编排。"""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from academic_paper_discovery.adapters.base import AdapterResult, PaperSource
from academic_paper_discovery.deduplication import deduplicate
from academic_paper_discovery.enrichment import extract_innovation
from academic_paper_discovery.impact import (
    load_bundled_metrics,
    resolve_impact_metric,
)
from academic_paper_discovery.models import (
    RecommendationTier,
    SearchRequest,
    SearchResult,
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
        impact_metrics: Mapping[str, str] | None = None,
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
        self.impact_metrics = (
    load_bundled_metrics()
    if impact_metrics is None
    else dict(impact_metrics)
)

    def run(self, request: SearchRequest) -> SearchResult:
        """执行检索；单个来源失败不会中断整次任务。"""

        plan = build_query_plan(request)
        adapter_results = self._search_sources(plan, request)

        candidates = []

        for adapter_result in adapter_results:
            remaining = self.total_candidate_limit - len(candidates)

            if remaining <= 0:
                break

            candidates.extend(
                adapter_result.papers[
                    : min(request.source_limit, remaining)
                ]
            )

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

        for paper in ranked:
            if paper.innovation == "未核验":
                paper.innovation = extract_innovation(paper.abstract)

            if paper.impact_metric == "未核验":
                paper.impact_metric = resolve_impact_metric(
                    paper.venue,
                    local_metrics=self.impact_metrics,
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

        results: list[AdapterResult | None] = [
            None
        ] * len(self.sources)

        worker_count = min(
            self.max_workers,
            len(self.sources),
        )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:
            futures: dict[
                Future[AdapterResult],
                int,
            ] = {
                executor.submit(
                    source.search,
                    plan,
                    request,
                ): index
                for index, source in enumerate(self.sources)
            }

            for future in as_completed(futures):
                index = futures[future]

                try:
                    results[index] = future.result()
                except Exception:
                    # 每个外部来源都有独立故障边界。
                    results[index] = AdapterResult()

        return [
            result
            for result in results
            if result is not None
        ]