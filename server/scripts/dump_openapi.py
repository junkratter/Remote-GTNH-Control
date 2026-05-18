"""Dump the OpenAPI spec to JSON for the frontend TS client generator.

Usage:
    python scripts/dump_openapi.py [out_path]
    # default out_path: ../website/src/api/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_out = repo_root / "website" / "src" / "api" / "openapi.json"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.main import create_app

    app = create_app()
    spec = app.openapi()
    out_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} ({len(spec.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
