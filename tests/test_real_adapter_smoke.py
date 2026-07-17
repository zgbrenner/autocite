import os

import pytest


pytestmark = pytest.mark.real_model


@pytest.mark.skipif(
    os.getenv("AUTOCITE_REAL_MODEL") != "1",
    reason="set AUTOCITE_REAL_MODEL=1 to load the real local adapter",
)
def test_published_adapter_real_smoke():
    from training.smoke_adapter import smoke

    import asyncio

    assert all(asyncio.run(smoke()).values())
