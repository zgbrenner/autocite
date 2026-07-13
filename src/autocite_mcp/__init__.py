"""AutoCite MCP: evidence-backed legal citation analysis and MCP tools."""

from .engine import CitationEngine
from .formatters import generate_citation

__all__ = ["CitationEngine", "generate_citation"]
__version__ = "0.3.0"
