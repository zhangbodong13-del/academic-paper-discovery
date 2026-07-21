from academic_paper_discovery.impact import resolve_impact_metric


LOCAL_METRICS = {
    "nature methods": "IF 25.8（2025 JCR）",
    "cvpr": "CCF A（2022版）/ CORE A*（2023版）",
}


def test_returns_local_journal_metric() -> None:
    assert resolve_impact_metric(
        "Nature Methods",
        local_metrics=LOCAL_METRICS,
    ) == "IF 25.8（2025 JCR）"


def test_returns_local_conference_metric_case_insensitively() -> None:
    assert resolve_impact_metric(
        "CVPR",
        local_metrics=LOCAL_METRICS,
    ) == "CCF A（2022版）/ CORE A*（2023版）"


def test_normalizes_extra_whitespace() -> None:
    assert resolve_impact_metric(
        "  Nature   Methods  ",
        local_metrics=LOCAL_METRICS,
    ) == "IF 25.8（2025 JCR）"


def test_uses_online_lookup_when_local_metric_is_missing() -> None:
    def online_lookup(venue: str) -> str | None:
        assert venue == "Unknown Journal"
        return "IF 8.2（2025 JCR）"

    assert resolve_impact_metric(
        "Unknown Journal",
        local_metrics=LOCAL_METRICS,
        online_lookup=online_lookup,
    ) == "IF 8.2（2025 JCR）"


def test_returns_unverified_when_no_metric_can_be_confirmed() -> None:
    assert resolve_impact_metric(
        "Unknown Venue",
        local_metrics=LOCAL_METRICS,
    ) == "未核验"


def test_returns_unverified_when_venue_is_missing() -> None:
    assert resolve_impact_metric(None, local_metrics=LOCAL_METRICS) == "未核验"
    assert resolve_impact_metric("", local_metrics=LOCAL_METRICS) == "未核验"
def test_loads_local_metrics_from_json(tmp_path) -> None:
    from academic_paper_discovery.impact import load_local_metrics

    config_path = tmp_path / "impact_metrics.json"
    config_path.write_text(
        """
{
  "Nature Methods": "IF 25.8（2025 JCR）",
  "CVPR": "CCF A（2022版）/ CORE A*（2023版）"
}
""".strip(),
        encoding="utf-8",
    )

    assert load_local_metrics(config_path) == {
        "Nature Methods": "IF 25.8（2025 JCR）",
        "CVPR": "CCF A（2022版）/ CORE A*（2023版）",
    }    