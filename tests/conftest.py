import pytest

from autocite_mcp import sources


@pytest.fixture(autouse=True)
def _clear_courtlistener_lookup_cache():
    """Keep the module-level lookup cache from leaking state between tests."""
    sources.clear_lookup_cache()
    yield
    sources.clear_lookup_cache()
