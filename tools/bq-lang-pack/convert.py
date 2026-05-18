#!/usr/bin/env python3
"""Convert BetterQuesting en_US.lang (BQ RU pack) to JSON for the web UI."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path


def _iter_entries(text: str):
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("###"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("betterquesting.quest.") or key.startswith(
            "betterquesting.questline."
        ):
            yield key, val


def convert_lang(text: str) -> dict[str, str]:
    return dict(_iter_entries(text))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="Path to BQ RU.zip or en_US.lang file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("website/public/bq-ru.json"),
        help="Output JSON path (default: website/public/bq-ru.json)",
    )
    args = parser.parse_args()
    src: Path = args.source
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as zf:
            name = "assets/betterquesting/lang/en_US.lang"
            text = zf.read(name).decode("utf-8", errors="replace")
    else:
        text = src.read_text(encoding="utf-8", errors="replace")
    data = convert_lang(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(data)} keys → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
