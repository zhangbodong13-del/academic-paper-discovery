from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.models import Paper, SearchRequest
from academic_paper_discovery.pipeline import SearchPipeline


class GoodSource:
    name = "good"

    def search(self, plan, request) -> AdapterResult:
        return AdapterResult(
            papers=[
                Paper(
                    title="Robot Microscope Autofocus",
                    doi="10.1000/auto",
                    source_names=["good"],
                ),
                Paper(
                    title="Robot Microscope Autofocus Duplicate",
                    doi="10.1000/AUTO",
                    source_names=["good-secondary"],
                ),
            ]
        )


class FailingSource:
    name = "failing"

    def search(self, plan, request) -> AdapterResult:
        raise RuntimeError("service unavailable")


class SkippedSource:
    name = "optional"

    def search(self, plan, request) -> AdapterResult:
        return AdapterResult()


def test_pipeline_continues_after_source_failure_without_status_data() -> None:
    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2026,
    )
    result = SearchPipeline(
        [GoodSource(), FailingSource(), SkippedSource()],
        current_year=2026,
    ).run(request)

    assert len(result.papers) == 1
    assert result.papers[0].source_names == ["good", "good-secondary"]
    assert "source_statuses" not in result.model_dump(mode="json")
    assert result.query_plan["original_topic"] == "robot microscope autofocus"


def test_pipeline_returns_empty_result_when_all_sources_fail() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)

    result = SearchPipeline([FailingSource()], current_year=2026).run(request)

    assert result.papers == []
    assert result.query_plan["assumptions"] == ["默认年份范围：2022-2026"]
    assert "source_statuses" not in result.model_dump(mode="json")


def test_pipeline_caps_total_candidates_before_ranking() -> None:
    class ManySource:
        name = "many"

        def search(self, plan, request) -> AdapterResult:
            papers = [Paper(title=f"Paper {index}") for index in range(10)]
            return AdapterResult(papers=papers)

    request = SearchRequest.with_defaults(
        topic="paper",
        current_year=2026,
        limit=10,
        source_limit=10,
    )

    result = SearchPipeline(
        [ManySource()],
        current_year=2026,
        total_candidate_limit=3,
    ).run(request)

    assert result.total_candidates == 3
    assert len(result.papers) == 3
def test_pipeline_extracts_innovation_from_abstract() -> None:
    class InnovationSource:
        name = "innovation-source"

        def search(self, plan, request) -> AdapterResult:
            return AdapterResult(
                papers=[
                    Paper(
                        title="Robot Microscope Autofocus",
                        abstract=(
                            "Autofocus is important in robotic microscopy. "
                            "We propose a disparity-aware method for robust "
                            "focus estimation."
                        ),
                        source_names=[self.name],
                    )
                ]
            )

    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
    )

    result = SearchPipeline(
        [InnovationSource()],
        current_year=2026,
    ).run(request)

    assert len(result.papers) == 1
    assert result.papers[0].innovation == (
        "摘要提取：We propose a disparity-aware method for robust "
        "focus estimation."
    )
def test_pipeline_resolves_impact_metric_from_local_mapping() -> None:
    class ImpactSource:
        name = "impact-source"

        def search(self, plan, request) -> AdapterResult:
            return AdapterResult(
                papers=[
                    Paper(
                        title="A Vision Conference Paper",
                        venue="CVPR",
                        source_names=[self.name],
                    )
                ]
            )

    request = SearchRequest.with_defaults(
        topic="computer vision",
        current_year=2026,
    )

    result = SearchPipeline(
        [ImpactSource()],
        current_year=2026,
        impact_metrics={
            "cvpr": "CCF A（2022版）/ CORE A*（2023版）",
        },
    ).run(request)

    assert len(result.papers) == 1
    assert result.papers[0].impact_metric == (
        "CCF A（2022版）/ CORE A*（2023版）"
    )    
def test_pipeline_uses_bundled_impact_metrics_by_default() -> None:
    class BundledImpactSource:
        name = "bundled-impact-source"

        def search(self, plan, request) -> AdapterResult:
            return AdapterResult(
                papers=[
                    Paper(
                        title="Computer Vision Conference Paper",
                        venue="CVPR",
                        source_names=[self.name],
                    )
                ]
            )

    request = SearchRequest.with_defaults(
        topic="computer vision",
        current_year=2026,
    )

    result = SearchPipeline(
        [BundledImpactSource()],
        current_year=2026,
    ).run(request)

    assert result.papers[0].impact_metric == (
        "CCF A（2022版）/ CORE A*（2023版）"
    )    
def test_pipeline_uses_online_lookup_when_local_metric_is_missing() -> None:
    class OnlineImpactSource:
        name = "online-impact-source"

        def search(self, plan, request) -> AdapterResult:
            return AdapterResult(
                papers=[
                    Paper(
                        title="A Journal Paper",
                        venue="Unknown Journal",
                        source_names=[self.name],
                    )
                ]
            )

    lookup_calls: list[str] = []

    def online_lookup(venue: str) -> str | None:
        lookup_calls.append(venue)
        return "IF 8.2（2025 JCR）"

    request = SearchRequest.with_defaults(
        topic="journal paper",
        current_year=2026,
    )

    result = SearchPipeline(
        [OnlineImpactSource()],
        current_year=2026,
        impact_metrics={},
        impact_online_lookup=online_lookup,
    ).run(request)

    assert result.papers[0].impact_metric == "IF 8.2（2025 JCR）"
    assert lookup_calls == ["Unknown Journal"]    