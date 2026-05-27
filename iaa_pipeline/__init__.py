"""IAA Pipeline — stage-aware inter-annotator agreement framework.

See iaa_pipeline_spec/ for full design documentation.
"""
from .aligners import (
    AlignmentResult,
    Stage2Alignment,
    align_by_key,
    align_stage1,
    align_stage2,
    align_stage3,
    align_stage4,
    align_stage5,
    align_error_types,
    align_relations_by_span,
)
from .metrics import (
    CategoricalAgreement,
    cohens_kappa,
    set_agreement,
    per_field_match_rate,
    compute_stage1_iaa,
    compute_stage2_iaa,
    compute_stage4_iaa,
    compute_error_type_iaa,
)

__version__ = "0.3.0"

__all__ = [
    # aligners
    "AlignmentResult",
    "Stage2Alignment",
    "align_by_key",
    "align_stage1",
    "align_stage2",
    "align_stage3",
    "align_stage4",
    "align_stage5",
    "align_error_types",
    "align_relations_by_span",
    # metrics
    "CategoricalAgreement",
    "cohens_kappa",
    "set_agreement",
    "per_field_match_rate",
    "compute_stage1_iaa",
    "compute_stage2_iaa",
    "compute_stage4_iaa",
    "compute_error_type_iaa",
]
