#!/usr/bin/env python3
"""Explicit legacy JSON remediation helper.

Use --dry-run first. --execute --confirm writes masked siblings. Add
--delete-source only after verification to remove the unsafe source file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.domain.privacy.remediation import scrub_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="JSON file or directory of legacy JSON files")
    parser.add_argument("--execute", action="store_true", help="write .masked.json siblings")
    parser.add_argument("--confirm", action="store_true", help="confirm the execute operation")
    parser.add_argument("--delete-source", action="store_true", help="delete source files after writing masks")
    args = parser.parse_args()
    if (args.execute or args.delete_source) and not args.confirm:
        parser.error("--execute/--delete-source requires --confirm")
    files = [args.path] if args.path.is_file() else sorted(args.path.rglob("*.json"))
    for source in files:
        payload = json.loads(source.read_text(encoding="utf-8"))
        masked, manifest = scrub_payload(payload)
        target = source.with_suffix(source.suffix + ".masked")
        print(f"{source}: {len(manifest['placeholders'])} placeholders -> {target}")
        if args.execute:
            target.write_text(json.dumps(masked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if args.delete_source:
                source.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
