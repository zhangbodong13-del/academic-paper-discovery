"""从可信论文元数据中提取报告增强信息。"""

from __future__ import annotations

import re


_ENGLISH_INNOVATION_PATTERNS = (
    r"\bwe propose\b",
    r"\bwe introduce\b",
    r"\bwe present\b",
    r"\bwe develop\b",
    r"\bwe design\b",
    r"\bwe devise\b",
    r"\bthis work proposes\b",
    r"\bthis work introduces\b",
    r"\bthis work presents\b",
    r"\bthis study proposes\b",
    r"\bthis study introduces\b",
)

_CHINESE_INNOVATION_MARKERS = (
    "本文提出",
    "本文引入",
    "本文设计",
    "本文开发",
    "本文构建",
    "本研究提出",
    "本研究引入",
    "我们提出",
    "我们引入",
    "首次提出",
)


def extract_innovation(abstract: str | None) -> str:
    """从摘要中提取包含明确创新行为的原句。

    只返回摘要中真实存在的句子，不根据标题或其他信息推测。
    找不到明确创新证据时返回“未核验”。
    """

    if abstract is None:
        return "未核验"

    cleaned = re.sub(r"\s+", " ", abstract).strip()
    if not cleaned:
        return "未核验"

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[。！？.!?])\s*",
            cleaned,
        )
        if sentence.strip()
    ]

    for sentence in sentences:
        normalized = sentence.casefold()

        if any(
            re.search(pattern, normalized)
            for pattern in _ENGLISH_INNOVATION_PATTERNS
        ):
            return f"摘要提取：{sentence}"

        if any(
            marker in sentence
            for marker in _CHINESE_INNOVATION_MARKERS
        ):
            return f"摘要提取：{sentence}"

    return "未核验"