"""The hedging linter: a deterministic check that an Inference statement
reads as a hypothesis, not a finding. See docs/EVIDENCE_MODEL.md section 5.

Crude by design. A false positive costs a line in a brief; a false negative
costs the credibility of the whole artifact. That trade is made deliberately
in one direction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ASSERTIVE_PATTERNS = [
    r"\bmanually enters?\b",
    r"\bcurrently uses?\b",
    r"\bhas no\b",
    r"\bhave no\b",
    r"\bstill relies? on\b",
    r"\btheir team spends?\b",
    r"\bprocess(?:ed|es|ing)?\b.{0,20}\bby hand\b",
    r"\blacks?\b",
    r"\bdoes not have\b",
    r"\bdo not have\b",
    r"\bis manually\b",
    r"\bare manually\b",
]

_HYPOTHESIS_MARKERS = [
    r"\bmay\b",
    r"\blikely\b",
    r"\bappears?\b",
    r"\bworth investigating\b",
    r"\bsuggests?\b",
    r"\bcould\b",
    r"\bplausibly\b",
    r"\bis a candidate for\b",
    r"\bmight\b",
    r"\bpotentially\b",
]

_ASSERTIVE_RE = re.compile("|".join(_ASSERTIVE_PATTERNS), re.IGNORECASE)
_MARKER_RE = re.compile("|".join(_HYPOTHESIS_MARKERS), re.IGNORECASE)


@dataclass
class LintResult:
    ok: bool
    reason: str | None = None


def lint_inference_statement(statement: str) -> LintResult:
    assertive_match = _ASSERTIVE_RE.search(statement)
    if assertive_match:
        return LintResult(
            ok=False,
            reason=f"contains assertive phrasing: {assertive_match.group(0)!r}",
        )
    if not _MARKER_RE.search(statement):
        return LintResult(
            ok=False,
            reason="contains no hypothesis marker (e.g. 'may', 'likely', 'worth investigating')",
        )
    return LintResult(ok=True)
