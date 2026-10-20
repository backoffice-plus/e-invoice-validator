#!/usr/bin/env python3
"""Add only missing SVRL report IDs without reserializing generated XPath namespaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SVRL = '{http://purl.oclc.org/dsdl/svrl}'
XSL = '{http://www.w3.org/1999/XSL/Transform}'
REPORT_TAG = re.compile(r'''<svrl:successful-report\b(?:[^>"']|"[^"]*"|'[^']*')*>''')
EXPECTED_REPORTS = {
    'FACTUR-X_MINIMUM.xslt': 11,
    'FACTUR-X_BASIC-WL.xslt': 59,
    'FACTUR-X_BASIC.xslt': 87,
    'FACTUR-X_EN16931.xslt': 194,
    'FACTUR-X_EXTENDED.xslt': 521,
}


def normalize(value: str) -> str:
    return ' '.join(value.split())


def enrich(path: Path) -> int:
    original = path.read_bytes()
    text = original.decode('utf-8')
    root = ET.fromstring(original)
    parents = {child: parent for parent in root.iter() for child in parent}
    reports = list(root.iter(SVRL + 'successful-report'))
    if len(reports) != EXPECTED_REPORTS[path.name]:
        raise ValueError(f'{path}: expected {EXPECTED_REPORTS[path.name]} reports, found {len(reports)}')
    tags = list(REPORT_TAG.finditer(text))
    if len(tags) != len(reports):
        raise ValueError(f'{path}: lexical and parsed report counts differ')
    replacements = []
    inserted = []
    identities = {}
    for index, (report, match) in enumerate(zip(reports, tags, strict=True)):
        native_id = report.get('id')
        if native_id and not native_id.startswith('FX-SCH-R-'):
            continue
        if report.find(f"{XSL}attribute[@name='id']") is not None:
            continue
        template = parents.get(report)
        while template is not None and template.tag != XSL + 'template':
            template = parents.get(template)
        if template is None or not template.get('match') or report.find(SVRL + 'text') is None:
            raise ValueError(f'{path}: report lacks a rule context or message')
        identity = [
            normalize(template.get('match', '')),
            normalize(report.attrib['test']),
            normalize(''.join(report.find(SVRL + 'text').itertext())),
        ]
        canonical = json.dumps(identity, ensure_ascii=False, separators=(',', ':'))
        report_id = 'FX-SCH-R-' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]
        if report_id in identities and identities[report_id] != canonical:
            raise ValueError(f'{path}: report ID hash collision for {report_id}')
        identities[report_id] = canonical
        if native_id:
            if native_id != report_id:
                raise ValueError(f'{path}: generated report ID differs from its identity: {native_id}')
            continue
        if match.group().endswith('/>'):
            raise ValueError(f'{path}: unexpected self-closing successful-report')
        replacements.append((match.end() - 1, f' id="{report_id}"'))
        inserted.append(index)

    enriched = text
    for position, attribute in reversed(replacements):
        enriched = enriched[:position] + attribute + enriched[position:]

    # The only parsed-tree difference must be the new metadata attributes. Lexical
    # insertion also preserves xmlns declarations used only inside XPath strings.
    verified = ET.fromstring(enriched)
    verified_reports = list(verified.iter(SVRL + 'successful-report'))
    for index in inserted:
        del verified_reports[index].attrib['id']
    if ET.tostring(root) != ET.tostring(verified):
        raise ValueError(f'{path}: report-ID insertion changed validation content')
    if replacements:
        path.write_bytes(enriched.encode('utf-8'))
    return len(replacements)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generated_root', type=Path)
    args = parser.parse_args()
    paths = sorted(args.generated_root.rglob('*.xslt'))
    if sorted(path.name for path in paths) != sorted(EXPECTED_REPORTS):
        raise ValueError('Expected exactly the five Factur-X 1.09.2 generated validators')
    for path in paths:
        print(f'{path.name}: added {enrich(path)} missing successful-report IDs')


if __name__ == '__main__':
    main()
