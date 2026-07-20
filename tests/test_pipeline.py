from academic_paper_discovery.adapters.base import AdapterResult
from academic_paper_discovery.models import Paper, SearchRequest, SourceStatus
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
            ],
            status=SourceStatus(
                source=self.name,
                state="success",
                result_count=2,
            ),
        )


class FailingSource:
    name = "failing"

    def search(self, plan, request) -> AdapterResult:
        raise RuntimeError("service unavailable")


class SkippedSource:
    name = "optional"

    def search(self, plan, request) -> AdapterResult:
        return AdapterResult(
            status=SourceStatus(
                source=self.name,
                state="skipped",
                message="未配置 API Key",
            )
        )


def test_pipeline_degrades_when_sources_fail_or_skip() -> None:
    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2026,
    )
    pipeline = SearchPipeline(
        [GoodSource(), FailingSource(), SkippedSource()],
        current_year=2026,
    )

    result = pipeline.run(request)

    assert [status.state for status in result.source_statuses] == [
        "success",
        "failed",
        "skipped",
    ]
    assert "service unavailable" in result.source_statuses[1].message
    assert len(result.papers) == 1
    assert result.papers[0].source_names == ["good", "good-secondary"]
    assert result.query_plan["original_topic"] == "robot microscope autofocus"


def test_pipeline_returns_auditable_empty_result_when_all_sources_fail() -> None:
    request = SearchRequest.with_defaults(
        topic="robot autofocus",
        current_year=2026,
    )

    result = SearchPipeline([FailingSource()], current_year=2026).run(request)

    assert result.papers == []
    assert result.source_statuses[0].state == "failed"
    assert result.query_plan["assumptions"] == ["默认年份范围：2022-2026"]


def test_pipeline_caps_total_candidates_before_ranking() -> None:
    class ManySource:
        name = "many"

        def search(self, plan, request) -> AdapterResult:
            papers = [Paper(title=f"Paper {index}") for index in range(10)]
            return AdapterResult(
                papers=papers,
                status=SourceStatus(
                    source=self.name,
                    state="success",
                    result_count=len(papers),
                ),
            )

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
