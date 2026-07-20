from pathlib import Path

from academic_paper_discovery.venues import VenueRegistry


def _registry() -> VenueRegistry:
    return VenueRegistry.from_yaml(Path("config/venues.yaml"))


def test_registry_matches_common_aliases() -> None:
    registry = _registry()

    assert registry.match(name="NIPS").canonical_name == "NeurIPS"
    assert registry.match(name="TRO").canonical_name == (
        "IEEE Transactions on Robotics"
    )
    assert registry.match(name="Conference on Computer Vision and Pattern Recognition").canonical_name == "CVPR"


def test_registry_matches_issn_and_official_domain() -> None:
    registry = _registry()

    assert registry.match(issn="0028-0836").canonical_name == "Nature"
    assert registry.match(url="https://www.science.org/journal/scirobotics").family == (
        "Science family"
    )


def test_registry_keeps_tier_as_descriptive_metadata() -> None:
    match = _registry().match(name="MICCAI")

    assert match.type == "conference"
    assert match.tier_label == "重点领域会议"
