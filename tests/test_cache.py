from pathlib import Path

import pytest

from academic_paper_discovery.cache import MetadataCache


def test_cache_key_is_stable_for_parameter_order() -> None:
    first = MetadataCache.make_key(
        "crossref",
        {"query": "robot autofocus", "rows": 20},
    )
    second = MetadataCache.make_key(
        "crossref",
        {"rows": 20, "query": "robot autofocus"},
    )

    assert first == second


def test_cache_returns_valid_metadata(tmp_path: Path) -> None:
    cache = MetadataCache(tmp_path)
    cache.put(
        "key",
        b'{"title":"A Study"}',
        content_type="application/json",
        ttl_seconds=60,
        now=100.0,
    )

    assert cache.get("key", now=159.0) == b'{"title":"A Study"}'


def test_cache_discards_expired_entry(tmp_path: Path) -> None:
    cache = MetadataCache(tmp_path)
    cache.put(
        "key",
        b"<feed />",
        content_type="application/atom+xml",
        ttl_seconds=60,
        now=100.0,
    )

    assert cache.get("key", now=161.0) is None
    assert not cache.entry_path("key").exists()


def test_cache_discards_corrupt_entry(tmp_path: Path) -> None:
    cache = MetadataCache(tmp_path)
    path = cache.entry_path("key")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")

    assert cache.get("key", now=100.0) is None
    assert not path.exists()


def test_cache_refuses_pdf_payload(tmp_path: Path) -> None:
    cache = MetadataCache(tmp_path)

    with pytest.raises(ValueError, match="仅允许缓存元数据"):
        cache.put(
            "key",
            b"%PDF-1.7",
            content_type="application/pdf",
            ttl_seconds=60,
        )
