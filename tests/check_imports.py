"""Imports every module of the integration against a real Home Assistant.

hassfest and HACS only read the manifest, so neither can notice that the code asks Home Assistant
for something it doesn't have. This can: the entity descriptions are built at import, so a wrong
device class or entity category fails here.

    python tests/check_imports.py
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "custom_components.tokit_cooker"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    modules = sorted((ROOT / "custom_components" / "tokit_cooker").glob("*.py"))
    failed = 0
    for path in modules:
        name = PACKAGE if path.stem == "__init__" else f"{PACKAGE}.{path.stem}"
        try:
            importlib.import_module(name)
        except Exception as err:  # noqa: BLE001 - every failure gets reported, not just the first
            failed += 1
            print(f"FAILED {name}: {type(err).__name__}: {err}")
        else:
            print(f"ok     {name}")
    if not modules or failed:
        print(f"{failed} of {len(modules)} modules failed to import")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
