"""Frozen domain taxonomy: workflows, segments, systems, triggers, personas.

No logic lives here. This module is data only, so that changing the ICP model
means editing this file (and docs/ICP.md) rather than scattering enum-like
strings across the codebase. See docs/ICP.md for the rationale behind every
table below.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from types import MappingProxyType


class WorkflowID(StrEnum):
    """The nine workflow hypotheses, each mapped to a published Trelium agent.

    Closed by design (CLAUDE.md R11): the LLM selects from this list and
    cannot invent a tenth. See docs/ICP.md section 5.
    """

    PO_ORDER_ENTRY = "WF_PO_ORDER_ENTRY"
    QUOTING = "WF_QUOTING"
    ORDER_STATUS = "WF_ORDER_STATUS"
    SUPPLIER_PURCHASING = "WF_SUPPLIER_PURCHASING"
    INVOICE_MATCHING = "WF_INVOICE_MATCHING"
    INVOICE_FOLLOWUP = "WF_INVOICE_FOLLOWUP"
    PROPOSAL_FOLLOWUP = "WF_PROPOSAL_FOLLOWUP"
    REPORTING = "WF_REPORTING"
    COMPANY_STORE_SYNC = "WF_COMPANY_STORE_SYNC"


WORKFLOW_TO_TRELIUM_AGENT: MappingProxyType[WorkflowID, str] = MappingProxyType(
    {
        WorkflowID.PO_ORDER_ENTRY: "Order Entry / PO Entry Agent",
        WorkflowID.QUOTING: "Quoting Agent",
        WorkflowID.ORDER_STATUS: "Order Status Agent",
        WorkflowID.SUPPLIER_PURCHASING: "Supplier Purchasing Agent",
        WorkflowID.INVOICE_MATCHING: "Invoice Vouching / Matching Agent",
        WorkflowID.INVOICE_FOLLOWUP: "Invoice Follow-up Agent",
        WorkflowID.PROPOSAL_FOLLOWUP: "Proposal Follow-up Agent",
        WorkflowID.REPORTING: "Business Report Agent",
        WorkflowID.COMPANY_STORE_SYNC: "Company-Store-to-ERP Sync Agent",
    }
)


class SegmentLabel(StrEnum):
    """Raw segment label. Maps to a SegmentTier via SEGMENT_TIER_MAP below."""

    PROMO_DISTRIBUTOR = "promotional_products_distributor"
    PROMO_SUPPLIER = "promotional_products_supplier"
    DECORATOR_PRINT_SHOP = "decorator_print_shop"
    ADJACENT_BRANDED_MERCH = "adjacent_branded_merchandise"
    OPS_HEAVY_NON_PROMO = "operations_heavy_non_promo"
    OUT_OF_ICP = "out_of_icp"
    UNRESOLVED = "unresolved"


class SegmentTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    X = "X"
    UNRESOLVED = "UNRESOLVED"


SEGMENT_TIER_MAP: MappingProxyType[SegmentLabel, SegmentTier] = MappingProxyType(
    {
        SegmentLabel.PROMO_DISTRIBUTOR: SegmentTier.A,
        SegmentLabel.PROMO_SUPPLIER: SegmentTier.A,
        SegmentLabel.DECORATOR_PRINT_SHOP: SegmentTier.A,
        SegmentLabel.ADJACENT_BRANDED_MERCH: SegmentTier.B,
        SegmentLabel.OPS_HEAVY_NON_PROMO: SegmentTier.C,
        SegmentLabel.OUT_OF_ICP: SegmentTier.X,
        SegmentLabel.UNRESOLVED: SegmentTier.UNRESOLVED,
    }
)


class ScaleBand(StrEnum):
    SWEET_SPOT = "SWEET_SPOT"  # $50M-$500M
    LOWER_MID = "LOWER_MID"  # $20M-$50M
    LARGE = "LARGE"  # $500M-$1B
    ENTERPRISE = "ENTERPRISE"  # >$1B
    SMALL = "SMALL"  # $5M-$20M
    MICRO = "MICRO"  # <$5M
    UNKNOWN = "UNKNOWN"  # no sourced figure


class SystemClass(StrEnum):
    INDUSTRY_ORDER_SYSTEM = "INDUSTRY_ORDER_SYSTEM"
    ERP_ACCOUNTING = "ERP_ACCOUNTING"
    CRM = "CRM"
    SUPPLIER_DATA = "SUPPLIER_DATA"
    COMMERCE_STORE = "COMMERCE_STORE"
    GENERIC_OFFICE = "GENERIC_OFFICE"


# Known system names -> class. Not exhaustive; extraction may surface others,
# which are classified GENERIC_OFFICE-adjacent (i.e. ignored for class scoring)
# unless added here. Adding a system name is a human decision (CLAUDE.md R11
# spirit extends to this table too: keep docs/ICP.md section 4 in sync).
SYSTEM_NAME_TO_CLASS: MappingProxyType[str, SystemClass] = MappingProxyType(
    {
        "sage": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "commonsku": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "shopworks": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "printavo": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "distributorcentral": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "syncore": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "aim": SystemClass.INDUSTRY_ORDER_SYSTEM,
        "netsuite": SystemClass.ERP_ACCOUNTING,
        "sap": SystemClass.ERP_ACCOUNTING,
        "oracle": SystemClass.ERP_ACCOUNTING,
        "quickbooks": SystemClass.ERP_ACCOUNTING,
        "acumatica": SystemClass.ERP_ACCOUNTING,
        "dynamics": SystemClass.ERP_ACCOUNTING,
        "microsoft dynamics": SystemClass.ERP_ACCOUNTING,
        "salesforce": SystemClass.CRM,
        "hubspot": SystemClass.CRM,
        "promostandards": SystemClass.SUPPLIER_DATA,
        "sanmar": SystemClass.SUPPLIER_DATA,
        "s&s activewear": SystemClass.SUPPLIER_DATA,
        "alphabroder": SystemClass.SUPPLIER_DATA,
        "shopify": SystemClass.COMMERCE_STORE,
        "ordermygear": SystemClass.COMMERCE_STORE,
        "magento": SystemClass.COMMERCE_STORE,
        "adobe commerce": SystemClass.COMMERCE_STORE,
        "bigcommerce": SystemClass.COMMERCE_STORE,
        "woocommerce": SystemClass.COMMERCE_STORE,
        "gmail": SystemClass.GENERIC_OFFICE,
        "outlook": SystemClass.GENERIC_OFFICE,
        "google sheets": SystemClass.GENERIC_OFFICE,
        "excel": SystemClass.GENERIC_OFFICE,
        "slack": SystemClass.GENERIC_OFFICE,
    }
)


class Trigger(StrEnum):
    GROWTH_HIGH = "GROWTH_HIGH"
    GROWTH_MODERATE = "GROWTH_MODERATE"
    CONTRACTION = "CONTRACTION"
    ACQUISITION = "ACQUISITION"
    SYSTEM_MIGRATION = "SYSTEM_MIGRATION"
    OPS_HIRING = "OPS_HIRING"
    AP_AR_HIRING = "AP_AR_HIRING"
    NEW_FACILITY = "NEW_FACILITY"
    LEADERSHIP_CHANGE_OPS = "LEADERSHIP_CHANGE_OPS"
    MARGIN_PRESSURE = "MARGIN_PRESSURE"
    SERVICE_VOLUME = "SERVICE_VOLUME"


class OpsSubSignal(StrEnum):
    OPS_MULTISTEP_ORDER = "OPS_MULTISTEP_ORDER"
    OPS_CUSTOMIZATION = "OPS_CUSTOMIZATION"
    OPS_SUPPLIER_NETWORK = "OPS_SUPPLIER_NETWORK"
    OPS_COMPANY_STORES = "OPS_COMPANY_STORES"
    OPS_QUOTE_INTAKE = "OPS_QUOTE_INTAKE"
    OPS_SERVICE_TEAM = "OPS_SERVICE_TEAM"
    OPS_MULTI_SITE = "OPS_MULTI_SITE"
    OPS_RETURNS_EXCEPTIONS = "OPS_RETURNS_EXCEPTIONS"


OPS_SUBSIGNAL_POINTS: MappingProxyType[OpsSubSignal, int] = MappingProxyType(
    {
        OpsSubSignal.OPS_MULTISTEP_ORDER: 5,
        OpsSubSignal.OPS_CUSTOMIZATION: 4,
        OpsSubSignal.OPS_SUPPLIER_NETWORK: 4,
        OpsSubSignal.OPS_COMPANY_STORES: 4,
        OpsSubSignal.OPS_QUOTE_INTAKE: 3,
        OpsSubSignal.OPS_SERVICE_TEAM: 3,
        OpsSubSignal.OPS_MULTI_SITE: 3,
        OpsSubSignal.OPS_RETURNS_EXCEPTIONS: 2,
    }
)


class SourceTier(IntEnum):
    """1 = strongest (company primary), 6 = unsourced model output (discarded)."""

    COMPANY_PRIMARY = 1
    INDUSTRY_ASSOCIATION = 2
    JOB_POSTING = 3
    EXECUTIVE_PUBLIC_CONTENT = 4
    THIRD_PARTY_REPORTING = 5
    UNSOURCED = 6


class EvidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Band(StrEnum):
    PRIORITY = "PRIORITY"
    INVESTIGATE = "INVESTIGATE"
    WATCH = "WATCH"
    DEPRIORITIZE = "DEPRIORITIZE"


class Persona(StrEnum):
    COO_VP_OPERATIONS = "COO / VP Operations"
    PRESIDENT_CEO = "President / CEO"
    VP_TECHNOLOGY = "VP Technology"
    CFO = "CFO"
    CUSTOMER_EXPERIENCE_LEAD = "Customer Experience / Service Leadership"
    CIO_VP_TECHNOLOGY = "CIO / VP Technology"
    OWNER_CEO = "Owner / CEO"
    OPERATIONS_MANAGER = "Operations Manager"


# (segment_tier_group, scale_band) -> (primary persona, secondary persona, rationale)
# segment_tier_group is one of "distributor", "supplier", "decorator", "other"
PERSONA_MAP: MappingProxyType[tuple[str, str], tuple[Persona, Persona, str]] = MappingProxyType(
    {
        ("distributor", "small_or_below"): (
            Persona.COO_VP_OPERATIONS,
            Persona.PRESIDENT_CEO,
            "At smaller distributors the COO or a hands-on President typically "
            "owns day-to-day order operations directly.",
        ),
        ("distributor", "large_or_above"): (
            Persona.VP_TECHNOLOGY,
            Persona.CFO,
            "At larger distributors, operational workflow ownership tends to sit "
            "with a VP Technology or transformation lead, with finance co-sponsoring "
            "cost-reduction cases.",
        ),
        ("supplier", "any"): (
            Persona.COO_VP_OPERATIONS,
            Persona.CUSTOMER_EXPERIENCE_LEAD,
            "Suppliers route distributor PO intake and status requests through "
            "operations and customer-experience functions.",
        ),
        ("decorator", "any"): (
            Persona.OWNER_CEO,
            Persona.OPERATIONS_MANAGER,
            "Decorators and print shops are typically owner-operated or run by a "
            "hands-on operations manager who owns production workflow.",
        ),
        ("other", "any"): (
            Persona.COO_VP_OPERATIONS,
            Persona.CFO,
            "Default operations-and-finance pairing for operations-heavy "
            "non-promo businesses.",
        ),
    }
)
