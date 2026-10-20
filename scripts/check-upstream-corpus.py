#!/usr/bin/env python3
"""Verify the pinned upstream test inputs before executing them."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'test-data/upstream'
HASH_LINE = re.compile(r'([0-9a-f]{64})  (.+)')


def main() -> int:
    try:
        for source in ('en16931', 'kosit', 'mustang'):
            directory = ROOT / source
            if not directory.is_dir() or not list(directory.rglob('SHA256SUMS')):
                raise ValueError(f'Missing pinned upstream corpus: {source}')
        checked = set()
        inventories = sorted(ROOT.rglob('SHA256SUMS'))
        for inventory in inventories:
            records = inventory.read_text(encoding='utf-8').splitlines()
            if not records:
                raise ValueError(f'Empty source inventory: {inventory}')
            local_paths = set()
            for line in records:
                match = HASH_LINE.fullmatch(line)
                if not match:
                    raise ValueError(f'Malformed source inventory line in {inventory}: {line!r}')
                expected, relative = match.groups()
                path = (inventory.parent / relative).resolve()
                if not path.is_relative_to(inventory.parent.resolve()) or not path.is_file():
                    raise ValueError(f'Missing source or path outside inventory: {relative}')
                if path in local_paths:
                    raise ValueError(f'Duplicate source inventory entry: {relative}')
                local_paths.add(path)
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError(f'Upstream source SHA-256 mismatch: {path.relative_to(ROOT)}')
                checked.add(path)
        xml_assets = {
            path.resolve() for path in ROOT.rglob('*')
            if path.is_file() and path.suffix.lower() in {'.xml', '.xsl', '.xslt', '.sch'}
        }
        if xml_assets - checked:
            missing = sorted(str(path.relative_to(ROOT)) for path in xml_assets - checked)
            raise ValueError(f'Unpinned upstream XML assets: {missing}')
        print(f'Upstream corpus check passed: {len(checked)} pinned files in {len(inventories)} inventories.')
        return 0
    except (OSError, ValueError) as error:
        print(f'Upstream corpus check failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
