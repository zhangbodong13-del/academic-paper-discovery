from academic_paper_discovery.models import Paper, PaperLink, SearchRequest
from academic_paper_discovery.query_plan import build_query_plan
from academic_paper_discovery.ranking import rank_papers


def _request_and_plan():
    request = SearchRequest.with_defaults(
        topic="robot microscope autofocus",
        current_year=2026,
        year_from=2000,
        year_to=2026,
        target_venues=["ICRA"],
        prefer_code=True,
    )
    return request, build_query_plan(request)


def test_relevant_new_paper_can_outrank_old_highly_cited_paper() -> None:
    request, plan = _request_and_plan()
    relevant_new = Paper(
        title="Robot Microscope Autofocus",
        abstract="Automatic focus control for a robotic microscope.",
        year=2026,
        venue="ICRA",
        citation_count=10,
        is_formal=True,
        source_names=["Crossref", "DBLP"],
        links=[
            PaperLink(
                kind="code",
                url="https://github.com/example/autofocus",
                source="project",
            )
        ],
    )
    old_weak = Paper(
        title="General Image Processing",
        abstract="A broad overview of image filters.",
        year=2010,
        citation_count=1000,
        is_formal=True,
        source_names=["Crossref"],
    )

    ranked = rank_papers(
        [old_weak, relevant_new],
        request,
        plan,
        current_year=2026,
    )

    assert ranked[0].title == "Robot Microscope Autofocus"
    assert ranked[0].score > ranked[1].score
    assert ranked[0].tier.value == "must-read"
    assert "标题" in ranked[0].why_read


def test_ranking_exposes_component_scores() -> None:
    request, plan = _request_and_plan()
    paper = Paper(
        title="Robot Microscope Autofocus",
        year=2025,
        venue="ICRA",
        source_names=["Crossref", "DBLP"],
        is_formal=True,
    )

    ranked = rank_papers([paper], request, plan, current_year=2026)[0]

    assert ranked.score_components["title_relevance"] == 1.0
    assert ranked.score_components["target_venue"] == 1.0
    assert ranked.score_components["multi_source"] > 0
    assert ranked.score_components["formal_version"] == 1.0


def test_ranking_uses_normalized_title_as_stable_tie_breaker() -> None:
    request = SearchRequest.with_defaults(
        topic="unmatched topic",
        current_year=2026,
        year_from=2020,
        year_to=2026,
    )
    plan = build_query_plan(request)

    ranked = rank_papers(
        [Paper(title="Beta"), Paper(title="Alpha")],
        request,
        plan,
        current_year=2026,
    )

    assert [paper.title for paper in ranked] == ["Alpha", "Beta"]
