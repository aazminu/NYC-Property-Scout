"""NYC Property Scout Utilities Package."""

from .bbl_matcher import BBLMatcher
from .property_analytics import (
    audit_property_records,
    coerce_numeric,
    compute_investment_metrics,
    decompose_bbl,
    filter_property_records,
    find_spatial_comps,
    haversine_km,
    normalize_bbl,
)

try:
    from .cloudant_uploader import CloudantUploader
except ImportError:
    CloudantUploader = None  # type: ignore[assignment]

__all__ = [
    "BBLMatcher",
    "CloudantUploader",
    "audit_property_records",
    "coerce_numeric",
    "compute_investment_metrics",
    "decompose_bbl",
    "filter_property_records",
    "find_spatial_comps",
    "haversine_km",
    "normalize_bbl",
]
