from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def generate(lockfile: Path) -> dict:
    text = Path(lockfile).read_text(encoding="utf-8")
    components = []
    for block in text.split("[[package]]")[1:]:
        name = re.search(r'^name = "([^"]+)"', block, re.M)
        version = re.search(r'^version = "([^"]+)"', block, re.M)
        if name and version:
            components.append(
                {
                    "type": "library",
                    "name": name.group(1),
                    "version": version.group(1),
                    "purl": f"pkg:pypi/{name.group(1)}@{version.group(1)}",
                }
            )
    unique = {(item["name"], item["version"]): item for item in components}
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "autocite-mcp"}},
        "components": [unique[key] for key in sorted(unique)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=Path("uv.lock"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(generate(args.lock), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
