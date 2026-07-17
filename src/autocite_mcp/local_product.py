from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any


INSTALL_PROFILES = {
    "lightweight": {"extras": (), "models": (), "network_allowed": False},
    "standard": {"extras": ("slm", "retrieval"), "models": ("qwen", "bge"), "network_allowed": True},
    "gpu": {"extras": ("slm", "slm-quantized", "retrieval", "retrieval-reranker"), "models": ("qwen", "bge", "reranker"), "network_allowed": True},
    "offline": {"extras": ("slm", "retrieval"), "models": ("predownloaded",), "network_allowed": False},
}


def installation_plan(profile: str) -> dict[str, Any]:
    if profile not in INSTALL_PROFILES:
        raise ValueError(f"profile must be one of {sorted(INSTALL_PROFILES)}")
    selected = INSTALL_PROFILES[profile]
    return {
        "schema_version": "1.0",
        "profile": profile,
        "optional_extras": list(selected["extras"]),
        "models_required": list(selected["models"]),
        "network_allowed": selected["network_allowed"],
        "automatic_download": False,
        "safe_defaults": {
            "transport": "stdio",
            "http_host": "127.0.0.1",
            "offline_review": True,
            "telemetry": False,
            "document_logging": False,
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ModelManager:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def _model_path(self, model_id: str) -> Path:
        if not model_id or Path(model_id).name != model_id or model_id in {".", ".."}:
            raise ValueError("model_id must be one safe path segment")
        return self.root / model_id

    def install_local(self, model_id: str, source: Path) -> dict[str, Any]:
        source_path = Path(source).expanduser().resolve()
        target = self._model_path(model_id)
        if not source_path.is_dir():
            raise ValueError("source must be an existing local directory")
        if target.exists():
            raise FileExistsError(f"model already installed: {model_id}")
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, target, symlinks=False)
        files = {
            str(path.relative_to(target)): _sha256(path)
            for path in sorted(target.rglob("*"))
            if path.is_file() and path.name != "autocite-model.json"
        }
        manifest = {"schema_version": "1.0", "model_id": model_id, "files": files}
        (target / "autocite-model.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"model_id": model_id, "path": str(target), **self.verify(model_id)}

    def list_models(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        results: list[dict[str, Any]] = []
        for path in sorted(item for item in self.root.iterdir() if item.is_dir()):
            size = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
            results.append(
                {
                    "model_id": path.name,
                    "path": str(path),
                    "size_bytes": size,
                    "manifest_present": (path / "autocite-model.json").is_file(),
                }
            )
        return results

    def verify(self, model_id: str) -> dict[str, Any]:
        target = self._model_path(model_id)
        manifest_path = target / "autocite-model.json"
        if not manifest_path.is_file():
            return {"verified": False, "mismatches": ["manifest_missing"]}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches: list[str] = []
        for relative, expected in manifest.get("files", {}).items():
            path = target / relative
            if not path.is_file() or _sha256(path) != expected:
                mismatches.append(relative)
        return {"verified": not mismatches, "mismatches": mismatches}

    def remove(self, model_id: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ValueError("confirm=True is required to remove a model")
        target = self._model_path(model_id)
        if not target.exists():
            return {"model_id": model_id, "removed": False, "reason": "not_installed"}
        shutil.rmtree(target)
        return {"model_id": model_id, "removed": True, "recoverable": False}


def default_model_root() -> Path:
    configured = os.getenv("AUTOCITE_MODEL_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".local" / "share" / "autocite" / "models"


def health_report(*, model_root: Path | None = None, offline: bool = True) -> dict[str, Any]:
    manager = ModelManager(model_root or default_model_root())
    models = manager.list_models()
    return {
        "schema_version": "1.0",
        "status": "ok",
        "service": "autocite-mcp",
        "operating_modes": ["stdio", "loopback_http", "python_api", "cli", "desktop_sidecar"],
        "platform": {"system": platform.system(), "machine": platform.machine(), "python": platform.python_version()},
        "privacy": {
            "telemetry": False,
            "document_logging": False,
            "diagnostic_logging": "redacted",
            "temporary_files": "in-memory by default; caller-selected exports only",
            "cleanup": "no retained review documents",
        },
        "network": {
            "review_default": "disabled",
            "offline_enforced": offline,
            "capable_components": ["explicit CourtListener verification", "explicit model installation"],
            "http_default_bind": "127.0.0.1",
        },
        "installed_models": models,
        "offline_ready": True,
        "deterministic_ready": True,
        "local_ml_ready": any(item["manifest_present"] for item in models),
    }
