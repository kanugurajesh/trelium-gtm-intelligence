"""E1/E2 verification, source-tier classification, and domain independence.

This module is what makes the project's central claim checkable rather than
asserted: E2 (``verify_quote``) is a plain substring comparison, not a
similarity score or an LLM judgment. An extraction that paraphrases a source,
invents a quote, or mis-cites a page fails it deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from trelium_gtm.evidence.store import sha256_text
from trelium_gtm.models import Evidence
from trelium_gtm.taxonomy import SourceTier

_JOB_POSTING_DOMAINS = {"indeed.com", "linkedin.com", "ziprecruiter.com", "glassdoor.com"}
_INDUSTRY_ASSOCIATION_DOMAINS = {"ppai.org", "asicentral.com"}
_EXEC_CONTENT_PATH_HINTS = ("/posts/", "/pulse/")  # LinkedIn post/article URL shapes


@dataclass
class VerificationResult:
    ok: bool
    reason: str | None = None


def registrable_domain(url: str) -> str:
    """Best-effort registrable domain: strips scheme, 'www.', and path.

    This is a heuristic, not a public-suffix-list implementation: it treats
    the last two dot-separated labels as the registrable domain, which is
    wrong for domains like 'example.co.uk' (yields 'co.uk'). Documented
    limitation; acceptable here because it is used only to avoid double
    counting two pages of the same obvious company site as two sources,
    not as a security boundary.
    """
    netloc = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    netloc = netloc.split(":")[0]  # drop port
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parts = netloc.split(".")
    if len(parts) <= 2:
        return netloc
    return ".".join(parts[-2:])


def classify_source_tier(source_url: str, company_domain: str) -> SourceTier:
    """Heuristic tier assignment. See docs/EVIDENCE_MODEL.md section 3."""
    domain = registrable_domain(source_url)
    company_reg_domain = registrable_domain(company_domain)

    if domain == company_reg_domain:
        return SourceTier.COMPANY_PRIMARY
    if domain in _INDUSTRY_ASSOCIATION_DOMAINS:
        return SourceTier.INDUSTRY_ASSOCIATION
    if domain in _JOB_POSTING_DOMAINS and "/jobs" in source_url.lower():
        return SourceTier.JOB_POSTING
    if domain == "linkedin.com" and any(h in source_url for h in _EXEC_CONTENT_PATH_HINTS):
        return SourceTier.EXECUTIVE_PUBLIC_CONTENT
    return SourceTier.THIRD_PARTY_REPORTING


def verify_hash(evidence: Evidence, snapshot_text: str) -> VerificationResult:
    """E1: sha256(snapshot_file) == Evidence.content_sha256."""
    actual = sha256_text(snapshot_text)
    if actual != evidence.content_sha256:
        return VerificationResult(
            ok=False,
            reason=f"E1 hash mismatch: stored={evidence.content_sha256[:12]}... actual={actual[:12]}...",
        )
    return VerificationResult(ok=True)


def verify_quote(evidence: Evidence, snapshot_text: str) -> VerificationResult:
    """E2: snapshot[offset:offset+len(quote)] == quote, exactly."""
    start = evidence.quote_offset
    end = start + len(evidence.quote)
    if start < 0 or end > len(snapshot_text):
        return VerificationResult(
            ok=False,
            reason=f"E2 offset out of bounds: [{start}:{end}] in snapshot of length {len(snapshot_text)}",
        )
    actual_span = snapshot_text[start:end]
    if actual_span != evidence.quote:
        return VerificationResult(
            ok=False,
            reason=(
                "E2 quote mismatch at offset "
                f"{start}: expected {evidence.quote!r}, found {actual_span!r}"
            ),
        )
    return VerificationResult(ok=True)


def find_quote_offset(snapshot_text: str, quote: str) -> int | None:
    """Fallback offset derivation (docs/IMPLEMENTATION_PLAN.md R3 mitigation):
    if the model's own offset is unreliable, search for the quote in the
    snapshot and use the offset only when the quote occurs exactly once.
    Returns None if zero or more-than-one occurrences are found.
    """
    first = snapshot_text.find(quote)
    if first == -1:
        return None
    second = snapshot_text.find(quote, first + 1)
    if second != -1:
        return None  # ambiguous - not a unique occurrence
    return first


def verify_evidence(evidence: Evidence, snapshot_text: str) -> VerificationResult:
    """Run E1 then E2. E1 failing short-circuits E2 (a bad snapshot makes any
    offset check meaningless)."""
    hash_result = verify_hash(evidence, snapshot_text)
    if not hash_result.ok:
        return hash_result
    return verify_quote(evidence, snapshot_text)


def independent_domain_count(evidence_list: list[Evidence]) -> int:
    return len({registrable_domain(e.source_url) for e in evidence_list})
