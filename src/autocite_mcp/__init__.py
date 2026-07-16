"""AutoCite MCP: evidence-backed legal citation analysis and MCP tools."""

from .engine import CitationEngine
from .formatters import generate_citation
from .slm import SLMProposal, validate_proposal

__all__ = ["CitationEngine", "SLMProposal", "generate_citation", "validate_proposal"]
__version__ = "0.4.0"
