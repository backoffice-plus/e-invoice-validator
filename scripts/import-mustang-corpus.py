#!/usr/bin/env python3
"""Import or verify the pinned, complete Mustang invoice XML fixtures offline."""

from __future__ import annotations

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


COMMIT = 'd3d51fd01a6a9c1fa4401bc8c08049e3dd0d7020'
ARCHIVE_SHA256 = '845a2bf0d4636ba68446aec99bc771817f228510655eab9df8ec2298066d227c'
ARCHIVE_PREFIX = f'mustangproject-{COMMIT}/'
DESTINATION = Path(__file__).resolve().parents[1] / 'test-data/upstream/mustang'
INVOICE_ROOTS = {'CrossIndustryInvoice', 'CrossIndustryDocument', 'Invoice', 'CreditNote'}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_files(archive: Path) -> dict[str, bytes]:
    content = archive.read_bytes()
    if sha256(content) != ARCHIVE_SHA256:
        raise ValueError('archive SHA-256 differs from the pinned Mustang commit archive')

    files: dict[str, bytes] = {}
    legacy_count = 0
    with zipfile.ZipFile(archive) as source:
        for name in ('LICENSE', 'NOTICE'):
            files[name] = source.read(ARCHIVE_PREFIX + name)
        for member in source.namelist():
            if not member.startswith(ARCHIVE_PREFIX):
                raise ValueError(f'unexpected archive root: {member}')
            relative = member.removeprefix(ARCHIVE_PREFIX)
            if '/src/test/resources/' not in relative or not relative.lower().endswith('.xml'):
                continue
            document = source.read(member)
            try:
                root = ET.fromstring(document)
            except ET.ParseError:
                continue
            root_name = root.tag.rsplit('}', 1)[-1]
            if root_name not in INVOICE_ROOTS:
                continue
            files[f'fixtures/{relative}'] = document
            legacy_count += root_name == 'CrossIndustryDocument'

    if len(files) != 100 or legacy_count != 9:
        raise ValueError(
            f'expected 98 invoice XML files, 9 legacy documents, LICENSE and NOTICE; '
            f'found {len(files) - 2} invoices and {legacy_count} legacy documents'
        )
    return files


def run(archive: Path, check: bool) -> None:
    files = source_files(archive)
    inventory = ''.join(f'{sha256(content)}  {name}\n' for name, content in sorted(files.items()))
    if check:
        for name, content in files.items():
            path = DESTINATION / name
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'missing or modified upstream file: {name}')
        fixture_paths = {
            str(path.relative_to(DESTINATION))
            for path in (DESTINATION / 'fixtures').rglob('*')
            if path.is_file()
        }
        if fixture_paths != {name for name in files if name.startswith('fixtures/')}:
            raise ValueError('vendored fixture set differs from the complete pinned invoice set')
        if (DESTINATION / 'SHA256SUMS').read_text(encoding='utf-8') != inventory:
            raise ValueError('SHA256SUMS differs from the pinned source inventory')
    else:
        for name, content in files.items():
            target = DESTINATION / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (DESTINATION / 'SHA256SUMS').write_text(inventory, encoding='utf-8')

    print(
        f'Mustang {COMMIT}: 98 original invoice XML files '
        f'{"verified" if check else "imported"}; 89 modern cases, 9 legacy exclusions. '
        'cases.json and provenance are maintained separately.'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path, help='local archive of the pinned commit')
    parser.add_argument('--check', action='store_true', help='verify without writing files')
    arguments = parser.parse_args()
    try:
        run(arguments.archive, arguments.check)
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
        print(f'Mustang import failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
