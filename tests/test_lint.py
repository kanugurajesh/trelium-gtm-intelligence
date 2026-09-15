"""The hedging linter must reject assertive claims about a company and
require an explicit hypothesis marker. CLAUDE.md R2.
"""

from __future__ import annotations

import pytest

from trelium_gtm.lint import lint_inference_statement


@pytest.mark.parametrize(
    "statement",
    [
        "Stran manually enters purchase orders into ShopWorks.",
        "The company currently uses spreadsheets for order tracking.",
        "They have no automated invoice matching process.",
        "Their team spends hours reconciling invoices by hand.",
        "The company lacks a modern ERP system.",
        "Orders are processed by hand at intake.",
    ],
)
def test_rejects_assertive_statements(statement):
    result = lint_inference_statement(statement)
    assert not result.ok
    assert "assertive" in result.reason


@pytest.mark.parametrize(
    "statement",
    [
        "Order entry may be a manual, multi-step process worth investigating at Stran.",
        "Given the company's growth signals, invoice matching automation could be relevant here.",
        "This suggests quote-to-order handoff is a candidate for automation.",
        "Inbound PO handling potentially crosses several systems and is worth probing.",
    ],
)
def test_accepts_hedged_statements(statement):
    result = lint_inference_statement(statement)
    assert result.ok


def test_rejects_statement_with_no_hedge_marker_even_if_not_assertive():
    result = lint_inference_statement("This is an interesting company in the promo space.")
    assert not result.ok
    assert "hypothesis marker" in result.reason
