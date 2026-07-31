"""AutoCite MCP: evidence-backed legal citation analysis and MCP tools."""

from .engine import CitationEngine
from .citation_graph import (
    AuthorityNode,
    CitationEdge,
    CitationGraph,
    OccurrenceNode,
    ResolutionResult,
    build_citation_graph,
)
from .document_ir import CitationLocation, CitationOccurrence, DocumentBlock, DocumentIR
from .deterministic_rules import RuleFinding, RuleSpec, evaluate_document_rules
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
    "AuthorityNode",
    "CitationEdge",
    "CitationGraph",
    "CitationLocation",
    "CitationOccurrence",
    "DocumentBlock",
    "DocumentIR",
    "RuleFinding",
    "RuleSpec",
    "OccurrenceNode",
    "ResolutionResult",
    "CitationProposal",
    "CitationProposalModel",
    "DisabledProposalModel",
    "LocalQwenProposalModel",
    "ModelRuntimeConfig",
    "SLMProposal",
    "generate_citation",
    "build_citation_graph",
    "evaluate_document_rules",
    "validate_proposal",
]
__version__ = "0.6.0"
