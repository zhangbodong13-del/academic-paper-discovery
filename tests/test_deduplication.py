from academic_paper_discovery.deduplication import deduplicate
from academic_paper_discovery.models import Paper, PaperLink


def test_deduplicate_uses_exact_doi_first() -> None:
    papers = [
        Paper(title="First Title", doi="10.1000/ABC", source_names=["Crossref"]),
        Paper(title="Different Metadata", doi="https://doi.org/10.1000/abc", source_names=["OpenAlex"]),
    ]

    merged = deduplicate(papers)

    assert len(merged) == 1
    assert merged[0].source_names == ["Crossref", "OpenAlex"]


def test_deduplicate_merges_arxiv_versions() -> None:
    papers = [
        Paper(title="A Tool Method", arxiv_id="2401.12345v1"),
        Paper(title="A Tool Method Revised", arxiv_id="2401.12345v2"),
    ]

    assert len(deduplicate(papers)) == 1


def test_formal_version_wins_and_keeps_preprint_links() -> None:
    preprint = Paper(
        title="Stereo Tool Pose Estimation",
        authors=["Ana Li"],
        year=2024,
        arxiv_id="2401.12345",
        is_formal=False,
        links=[
            PaperLink(
                kind="preprint",
                url="https://arxiv.org/abs/2401.12345",
                source="arXiv",
            )
        ],
        source_names=["arXiv"],
    )
    formal = Paper(
        title="Stereo Tool Pose Estimation",
        authors=["Ana Li", "Bo Zhang"],
        year=2024,
        venue="MICCAI",
        doi="10.2000/tool",
        is_formal=True,
        links=[
            PaperLink(
                kind="publisher",
                url="https://doi.org/10.2000/tool",
                source="Crossref",
            )
        ],
        source_names=["Crossref"],
    )

    merged = deduplicate([preprint, formal])[0]

    assert merged.is_formal is True
    assert merged.venue == "MICCAI"
    assert merged.doi == "10.2000/tool"
    assert merged.arxiv_id == "2401.12345"
    assert [link.url for link in merged.links] == [
        "https://doi.org/10.2000/tool",
        "https://arxiv.org/abs/2401.12345",
    ]
    assert merged.source_names == ["Crossref", "arXiv"]


def test_fuzzy_title_requires_shared_author_and_nearby_year() -> None:
    first = Paper(
        title="Six Degree of Freedom Surgical Instrument Pose Estimation",
        authors=["Ana Li"],
        year=2024,
    )
    second = Paper(
        title="6-DoF Surgical Instrument Pose Estimation",
        authors=["Ana Li", "Bo Zhang"],
        year=2025,
    )

    assert len(deduplicate([first, second], fuzzy_threshold=75)) == 1


def test_low_confidence_candidate_stays_separate_with_warning() -> None:
    first = Paper(
        title="Robot Microscope Focus Estimation",
        authors=["Ana Li"],
        year=2024,
    )
    second = Paper(
        title="Robot Microscope Focus Control",
        authors=["Ana Li"],
        year=2024,
    )

    results = deduplicate(
        [first, second],
        fuzzy_threshold=95,
        low_confidence_threshold=70,
    )

    assert len(results) == 2
    assert all("可能重复" in paper.warnings for paper in results)
