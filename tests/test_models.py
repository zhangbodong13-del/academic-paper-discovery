import pytest
from pydantic import ValidationError

from academic_paper_discovery.models import Paper, SearchRequest, SearchResult


def test_search_request_exposes_default_year_assumption() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)

    assert (request.year_from, request.year_to) == (2022, 2026)
    assert request.limit == 20
    assert request.year_range_was_defaulted is True


def test_search_request_preserves_explicit_year_range() -> None:
    request = SearchRequest.with_defaults(
        topic="robot autofocus",
        current_year=2026,
        year_from=2020,
        year_to=2024,
    )

    assert (request.year_from, request.year_to) == (2020, 2024)
    assert request.year_range_was_defaulted is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"year_from": 2026, "year_to": 2022},
        {"limit": 101},
    ],
)
def test_search_request_rejects_invalid_constraints(overrides: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        SearchRequest.with_defaults(
            topic="robot autofocus",
            current_year=2026,
            **overrides,
        )


def test_paper_normalizes_doi() -> None:
    paper = Paper(title="A Study", doi="https://doi.org/10.1000/ABC")

    assert paper.doi == "10.1000/abc"


def test_paper_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        Paper(title="   ")


def test_search_result_serialization_has_no_source_statuses() -> None:
    request = SearchRequest.with_defaults(topic="robot autofocus", current_year=2026)
    query_plan = {"original_topic": "robot autofocus"}
    result = SearchResult(request=request, query_plan=query_plan)

    payload = result.model_dump(mode="json")

    assert "source_statuses" not in payload
    assert payload["query_plan"] == query_plan
