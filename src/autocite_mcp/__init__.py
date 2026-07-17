"""AutoCite MCP: evidence-backed legal citation analysis and MCP tools."""

from .engine import CitationEngine
from .formatters import generate_citation
from .proposal_models import (
    CitationProposalModel,
    DisabledProposalModel,
    LocalQwenProposalModel,
    ModelRuntimeConfig,
)
from .slm import CitationProposal, SLMProposal, validate_proposal

__all__ = [
    "CitationEngine",
    "CitationProposal",
    "CitationProposalModel",
    "DisabledProposalModel",
    "LocalQwenProposalModel",
    "ModelRuntimeConfig",
    "SLMProposal",
    "generate_citation",
    "validate_proposal",
]
__version__ = "0.4.0"
