#!/usr/bin/env python3
"""Reproduce the narrow BR-CO-09 Greek EL-prefix correction beside the upstream XSLT."""

from __future__ import annotations

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'configuration/xrechnung/3.0.2_2026-08-31/resources/en16931/1.3.17'
ORIGINAL = DIRECTORY / 'EN16931-UBL-validation.xslt'
CORRECTED = DIRECTORY / 'EN16931-UBL-validation-EL-corrected.xslt'
ORIGINAL_SHA256 = 'fc4e6cfa8596bba0c2abd19038a98960c6ee9fc1f44566787c115efd4f4aca7c'
CORRECTED_SHA256 = 'f8e2e46cac791bfa9b3886528f21221161425e62148dc46a66c517aa64de72ee'
XSL = '{http://www.w3.org/1999/XSL/Transform}'
SVRL = '{http://purl.oclc.org/dsdl/svrl}'


def correction(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('The official EN16931 UBL 1.3.17 source SHA-256 changed')
    original = ET.fromstring(source)
    parents = {child: parent for parent in original.iter() for child in parent}
    rules = [
        element for element in original.iter(SVRL + 'failed-assert')
        if element.get('id') == 'BR-CO-09'
        or element.findtext(f"{XSL}attribute[@name='id']") == 'BR-CO-09'
    ]
    if len(rules) != 1:
        raise ValueError('Expected exactly one BR-CO-09 assertion')
    assertion = rules[0]
    expression = assertion.attrib['test']
    if expression.count(' EG EH ER ') != 1 or ' EL ' in expression or ' GR ' not in expression:
        raise ValueError('Unexpected BR-CO-09 country-token list')
    choice = parents[parents[assertion]]
    conditions = [element for element in choice if element.tag == XSL + 'when']
    if choice.tag != XSL + 'choose' or len(conditions) != 1 or conditions[0].get('test') != expression:
        raise ValueError('The BR-CO-09 executable and reported predicates differ')
    revised = expression.replace(' EG EH ER ', ' EG EH EL ER ')
    before = escape(expression, {'"': '&quot;'}).encode('utf-8')
    after = escape(revised, {'"': '&quot;'}).encode('utf-8')
    if source.count(before) != 2:
        raise ValueError('Expected exactly two lexical BR-CO-09 predicate occurrences')
    result = source.replace(before, after)

    # Verify that only the executable predicate and the same SVRL diagnostic
    # predicate gained the EL token. IDs, severities, messages and all other
    # expressions must have identical parsed trees. Byte replacement preserves
    # the original namespace declarations, including XPath-only prefixes.
    checked = ET.fromstring(result)
    changed = 0
    for element in checked.iter():
        if element.get('test') == revised:
            if element.tag not in {XSL + 'when', SVRL + 'failed-assert'}:
                raise ValueError('Unexpected changed element')
            element.set('test', expression)
            changed += 1
    if changed != 2 or ET.tostring(original) != ET.tostring(checked):
        raise ValueError('The EL correction changed more than the two BR-CO-09 predicates')
    if hashlib.sha256(result).hexdigest() != CORRECTED_SHA256:
        raise ValueError('The EL correction SHA-256 differs from the reviewed derivative')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = correction(ORIGINAL.read_bytes())
    if args.check:
        if not CORRECTED.is_file() or CORRECTED.read_bytes() != expected:
            raise ValueError('The committed EN16931 UBL EL correction is missing or stale')
        print('EN16931 UBL EL correction is reproducible; original source and all other rules are unchanged.')
    else:
        CORRECTED.write_bytes(expected)
        print(f'Wrote {CORRECTED.relative_to(ROOT)}; SHA-256 {hashlib.sha256(expected).hexdigest()}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f'EN16931 UBL repair failed: {error}', file=sys.stderr)
        sys.exit(1)
