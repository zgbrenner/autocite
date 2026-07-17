from __future__ import annotations

from pathlib import Path

import pytest

from autocite_mcp.local_product import (
    INSTALL_PROFILES,
    ModelManager,
    health_report,
    installation_plan,
)
from autocite_mcp.hosting import validate_loopback_host


def test_install_profiles_are_explicit_and_local_first():
    assert set(INSTALL_PROFILES) == {"lightweight", "standard", "gpu", "offline"}
    assert installation_plan("lightweight")["models_required"] == []
    assert installation_plan("standard")["automatic_download"] is False
    assert installation_plan("offline")["network_allowed"] is False


def test_health_report_discloses_privacy_and_network_components(tmp_path: Path):
    report = health_report(model_root=tmp_path, offline=True)
    assert report["schema_version"] == "1.0"
    assert report["privacy"]["telemetry"] is False
    assert report["privacy"]["document_logging"] is False
    assert report["network"]["review_default"] == "disabled"
    assert report["offline_ready"] is True


def test_model_manager_installs_verifies_lists_and_removes_local_files(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "config.json").write_text('{"model":"fixture"}')
    manager = ModelManager(tmp_path / "models")
    installed = manager.install_local("fixture", source)
    assert installed["verified"] is True
    assert manager.list_models()[0]["model_id"] == "fixture"
    assert manager.verify("fixture")["verified"] is True
    removed = manager.remove("fixture", confirm=True)
    assert removed["removed"] is True


def test_model_removal_requires_confirmation(tmp_path: Path):
    manager = ModelManager(tmp_path / "models")
    with pytest.raises(ValueError, match="confirm"):
        manager.remove("anything", confirm=False)


def test_http_transport_rejects_public_bind_addresses():
    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"
    with pytest.raises(ValueError, match="loopback"):
        validate_loopback_host("0.0.0.0")
