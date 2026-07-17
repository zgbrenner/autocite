"""Source-family coverage declarations for deterministic citation rules."""

from .administrative import COVERAGE as ADMINISTRATIVE
from .ai_materials import COVERAGE as AI_MATERIALS
from .archival import COVERAGE as ARCHIVAL
from .books import COVERAGE as BOOKS
from .cases import COVERAGE as CASES
from .constitutions import COVERAGE as CONSTITUTIONS
from .court_documents import COVERAGE as COURT_DOCUMENTS
from .internet import COVERAGE as INTERNET
from .international import COVERAGE as INTERNATIONAL
from .journals import COVERAGE as JOURNALS
from .news import COVERAGE as NEWS
from .regulations import COVERAGE as REGULATIONS
from .statutes import COVERAGE as STATUTES

SOURCE_FAMILY_COVERAGE = {
    item["family"]: (item["status"], tuple(item["implemented_rules"]))
    for item in (
        CASES,
        STATUTES,
        REGULATIONS,
        CONSTITUTIONS,
        ADMINISTRATIVE,
        BOOKS,
        JOURNALS,
        NEWS,
        COURT_DOCUMENTS,
        INTERNET,
        ARCHIVAL,
        INTERNATIONAL,
        AI_MATERIALS,
    )
}

__all__ = ["SOURCE_FAMILY_COVERAGE"]
