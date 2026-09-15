"""JSON brief renderer. Thin wrapper: the schema itself (models.AccountBrief)
already defines the shape from docs/PROJECT_SPEC.md's required output schema.
"""

from __future__ import annotations

from trelium_gtm.models import AccountBrief


def render_brief_json(brief: AccountBrief) -> str:
    return brief.model_dump_json(indent=2)
