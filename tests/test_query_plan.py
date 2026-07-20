from academic_paper_discovery.models import SearchRequest
from academic_paper_discovery.query_plan import build_query_plan


def test_plan_keeps_multilingual_terms_and_assumptions() -> None:
    request = SearchRequest.with_defaults(
        topic="双目显微手术器械位姿估计",
        current_year=2026,
        expanded_queries=[
            "stereo microscopy",
            "surgical instrument pose estimation",
        ],
        target_venues=["MICCAI", "TMI"],
        exclusions=["education"],
    )

    plan = build_query_plan(request)

    assert plan.original_topic == request.topic
    assert plan.queries[0] == request.topic
    assert "stereo microscopy" in plan.queries
    assert plan.venue_queries == ["MICCAI", "TMI"]
    assert plan.exclusions == ["education"]
    assert "默认年份范围：2022-2026" in plan.assumptions


def test_plan_removes_duplicate_queries_without_reordering() -> None:
    request = SearchRequest.with_defaults(
        topic="Robot Autofocus",
        current_year=2026,
        expanded_queries=[
            " robot   autofocus ",
            "microscope autofocus",
            "MICROSCOPE AUTOFOCUS",
        ],
    )

    plan = build_query_plan(request)

    assert plan.queries == ["Robot Autofocus", "microscope autofocus"]


def test_plan_records_explicit_year_range_without_default_assumption() -> None:
    request = SearchRequest.with_defaults(
        topic="robot autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2024,
    )

    plan = build_query_plan(request)

    assert plan.assumptions == []
    assert (plan.year_from, plan.year_to) == (2020, 2024)
