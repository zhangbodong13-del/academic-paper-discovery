"""基于配置的期刊与会议识别。"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field


class VenueMatch(BaseModel):
    """命中的规范化 venue 元数据。"""

    model_config = ConfigDict(extra="forbid")

    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    type: str
    publisher: str
    family: str
    tier_label: str
    official_domains: list[str] = Field(default_factory=list)
    issn: list[str] = Field(default_factory=list)


class VenueRegistry:
    """按名称、ISSN 或官方域名匹配 venue。"""

    def __init__(self, venues: list[VenueMatch]) -> None:
        self.venues = venues
        self._name_index: dict[str, VenueMatch] = {}
        self._issn_index: dict[str, VenueMatch] = {}
        for venue in venues:
            for name in [venue.canonical_name, *venue.aliases]:
                self._name_index[_normalize_name(name)] = venue
            for issn in venue.issn:
                self._issn_index[_normalize_issn(issn)] = venue

    @classmethod
    def from_yaml(cls, path: Path) -> VenueRegistry:
        document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        venues = [VenueMatch.model_validate(item) for item in document.get("venues", [])]
        return cls(venues)

    def match(
        self,
        *,
        name: str | None = None,
        issn: str | None = None,
        url: str | None = None,
    ) -> VenueMatch | None:
        if issn and (match := self._issn_index.get(_normalize_issn(issn))):
            return match
        if name and (match := self._name_index.get(_normalize_name(name))):
            return match
        if url:
            hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
            for venue in self.venues:
                for domain in venue.official_domains:
                    normalized_domain = domain.lower().removeprefix("www.")
                    if hostname == normalized_domain or hostname.endswith(
                        f".{normalized_domain}"
                    ):
                        return venue
        return None


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9xX]", "", value).upper()
