"""论文重复识别和预印本/正式版本合并。"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from academic_paper_discovery.models import Paper, PaperLink


def deduplicate(
    papers: list[Paper],
    *,
    fuzzy_threshold: int = 92,
    low_confidence_threshold: int = 86,
) -> list[Paper]:
    """按可靠标识优先级合并重复论文。"""

    results: list[Paper] = []
    for original in papers:
        candidate = original.model_copy(deep=True)
        merged = False
        for index, existing in enumerate(results):
            decision, similarity = _match(existing, candidate, fuzzy_threshold)
            if decision:
                results[index] = _merge(existing, candidate)
                merged = True
                break
            if (
                similarity >= low_confidence_threshold
                and _authors_overlap(existing, candidate)
                and _years_near(existing, candidate)
            ):
                warning = "可能重复"
                if warning not in existing.warnings:
                    existing.warnings.append(warning)
                if warning not in candidate.warnings:
                    candidate.warnings.append(warning)
        if not merged:
            results.append(candidate)
    return results


def _match(first: Paper, second: Paper, fuzzy_threshold: int) -> tuple[bool, float]:
    if first.doi and second.doi and first.doi == second.doi:
        return True, 100.0
    first_arxiv = _normalize_arxiv_id(first.arxiv_id)
    second_arxiv = _normalize_arxiv_id(second.arxiv_id)
    if first_arxiv and second_arxiv and first_arxiv == second_arxiv:
        return True, 100.0

    first_title = _normalize_title(first.title)
    second_title = _normalize_title(second.title)
    if first_title == second_title:
        return True, 100.0

    similarity = float(fuzz.token_set_ratio(first_title, second_title))
    fuzzy_match = (
        similarity >= fuzzy_threshold
        and _authors_overlap(first, second)
        and _years_near(first, second)
    )
    return fuzzy_match, similarity


def _merge(first: Paper, second: Paper) -> Paper:
    winner, other = (
        (second, first)
        if second.is_formal and not first.is_formal
        else (first, second)
    )
    abstracts = [value for value in (winner.abstract, other.abstract) if value]
    citation_values = [
        value
        for value in (winner.citation_count, other.citation_count)
        if value is not None
    ]
    return winner.model_copy(
        update={
            "authors": _stable_strings([*winner.authors, *other.authors]),
            "year": winner.year or other.year,
            "venue": winner.venue or other.venue,
            "abstract": max(abstracts, key=len) if abstracts else None,
            "doi": winner.doi or other.doi,
            "arxiv_id": winner.arxiv_id or other.arxiv_id,
            "citation_count": max(citation_values) if citation_values else None,
            "publication_type": winner.publication_type or other.publication_type,
            "is_formal": winner.is_formal or other.is_formal,
            "links": _stable_links([*winner.links, *other.links]),
            "source_names": _stable_strings(
                [*winner.source_names, *other.source_names]
            ),
            "raw_ids": {**other.raw_ids, **winner.raw_ids},
            "warnings": _stable_strings([*winner.warnings, *other.warnings]),
        }
    )


def _normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\b6[\s-]*dof\b", "six degree of freedom", normalized)
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _normalize_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", normalized)
    normalized = normalized.removesuffix(".pdf")
    normalized = re.sub(r"v\d+$", "", normalized)
    return normalized or None


def _authors_overlap(first: Paper, second: Paper) -> bool:
    first_surnames = {_surname(author) for author in first.authors}
    second_surnames = {_surname(author) for author in second.authors}
    first_surnames.discard("")
    second_surnames.discard("")
    return bool(first_surnames & second_surnames)


def _surname(author: str) -> str:
    parts = author.casefold().split()
    return parts[-1] if parts else ""


def _years_near(first: Paper, second: Paper) -> bool:
    if first.year is None or second.year is None:
        return False
    return abs(first.year - second.year) <= 1


def _stable_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _stable_links(values: list[PaperLink]) -> list[PaperLink]:
    result: list[PaperLink] = []
    seen: set[str] = set()
    for link in values:
        if link.url not in seen:
            seen.add(link.url)
            result.append(link)
    return result
