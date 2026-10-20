#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FACTUR_X_ROOT = REPOSITORY_ROOT / 'configuration/factur-x/1.09.2'
XRECHNUNG_ROOT = REPOSITORY_ROOT / 'configuration/xrechnung/3.0.2_2026-08-31'
XRECHNUNG_CORPUS_ROOT = REPOSITORY_ROOT / 'test-data/valid-files/xrechnung-3.0.2'
FACTUR_X_RULE_ID_MAP = REPOSITORY_ROOT / 'tools/factur-x-xslt/rule-id-map.json'
XML_SUFFIXES = {'.xml', '.xsd', '.xsl', '.xslt', '.sch'}
DOCUMENT_REFERENCE = re.compile(r'''document\(\s*['\"]([^'\"]+)['\"]\s*\)''')
SCENARIO_NAMESPACE = 'http://www.xoev.de/de/validator/framework/1/scenarios'
NS = {'scenario': SCENARIO_NAMESPACE}
GENERIC_UBL_SOURCE = 'resources/en16931/1.3.17/EN16931-UBL-validation.xslt'
GENERIC_UBL_ACTIVE = 'resources/en16931/1.3.17/EN16931-UBL-validation-EL-corrected.xslt'

FACTUR_X_HASHES = {
    '0_Factur-X_1.09.2_MINIMUM': (
        'c570a628498e0b633a3dd66dd745653a8a2bc66fc6ee346b1971b9dc2d5f6778',
        '6d35419c2f10be60b8f7b035129b176e11b9c006c8d422053d0c8e25880230ec',
        '5c575cf37533a12a758f08b6b9691841c1691f2af214f21e040a07ec892e1f20',
    ),
    '1_Factur-X_1.09.2_BASICWL': (
        'c32dd6eb4ef9c3e88772726ff86aca796476b719152edd6d95aa96ddb17a63f0',
        'b5b8acca436e50086f84647d5e1ee7d4606b93dec41cfc3cfa1cb18b54c5b92b',
        'a34cd66dda00a9260368fa02dad97e966ded1c1ad100787a5318074328d20abb',
    ),
    '2_Factur-X_1.09.2_BASIC': (
        'b2a84cee0e497733bf595c435db18ba720a9f2e16f6741a972667a2f277f6bed',
        '733e08a96db7d59827b196eb2674b764bed8e54335073e4fa05b59b99d17938e',
        'a150b48359a72e1c1629edddb147d5133aabd03adb6ce8b3d287d0c2a6936d21',
    ),
    '3_Factur-X_1.09.2_EN16931': (
        'ef8c8380b499d1267b2dcf1fa709b45631a77d6d5f220c6cc2ade2fdade59473',
        '88b95d60df0c47e0c9cec15071c0583c9013bb80b2b9dc12b570c32af9af093d',
        '70339a41d71b02bb97683f8eea04acbd764e077a88a446b32860d89c3351b62f',
    ),
    '4_Factur-X_1.09.2_EXTENDED': (
        '5b9039e31f86e90f1a34925e84d3fad206efa3ca5639bb98a0cefd3661d3e36a',
        '8aae1322ce15e127b112cf2c8c84dc61c02e95c124261da0a6f297bd3e1a1853',
        '6e23aedbba0e3b32b3b1211d145186193215f56f755201555306c42327e75fbc',
    ),
}

FACTUR_X_FILES = {
    '0_Factur-X_1.09.2_MINIMUM': ('FACTUR-X_MINIMUM.sch', '_XSLT_MINIMUM/FACTUR-X_MINIMUM.xslt'),
    '1_Factur-X_1.09.2_BASICWL': ('FACTUR-X_BASIC-WL.sch', '_XSLT_BASIC-WL/FACTUR-X_BASIC-WL.xslt'),
    '2_Factur-X_1.09.2_BASIC': ('FACTUR-X_BASIC.sch', '_XSLT_BASIC/FACTUR-X_BASIC.xslt'),
    '3_Factur-X_1.09.2_EN16931': ('FACTUR-X_EN16931.sch', '_XSLT_EN16931/FACTUR-X_EN16931.xslt'),
    '4_Factur-X_1.09.2_EXTENDED': ('FACTUR-X_EXTENDED.sch', '_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt'),
}


def fail(message: str) -> None:
    raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def parse_xml_assets() -> int:
    parsed = 0
    for configuration_root in (FACTUR_X_ROOT, XRECHNUNG_ROOT):
        for path in sorted(configuration_root.rglob('*')):
            if path.is_file() and path.suffix.lower() in XML_SUFFIXES:
                try:
                    ET.parse(path)
                except ET.ParseError as error:
                    fail(f'Invalid XML asset {path.relative_to(REPOSITORY_ROOT)}: {error}')
                parsed += 1
    return parsed


def check_offline_reference_closure() -> int:
    checked = 0
    for configuration_root in (FACTUR_X_ROOT, XRECHNUNG_ROOT):
        for path in sorted(configuration_root.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in XML_SUFFIXES:
                continue
            root = ET.parse(path).getroot()
            for element in root.iter():
                name = local_name(element.tag)
                references: list[str] = []
                if name == 'location' and element.text:
                    references.append(element.text.strip())
                elif name in {'import', 'include', 'override', 'redefine'}:
                    references.extend(
                        element.attrib[key]
                        for key in ('schemaLocation', 'href')
                        if key in element.attrib
                    )

                for reference in references:
                    parts = urlsplit(reference)
                    if parts.scheme or parts.netloc:
                        fail(
                            f'Runtime network reference in {path.relative_to(REPOSITORY_ROOT)}: '
                            f'{reference}'
                        )
                    decoded_path = unquote(parts.path)
                    target = (
                        configuration_root / decoded_path
                        if name == 'location'
                        else path.parent / decoded_path
                    )
                    if not target.is_file():
                        fail(
                            f'Missing referenced asset from {path.relative_to(REPOSITORY_ROOT)}: '
                            f'{reference}'
                        )
                    checked += 1

            text = path.read_text(encoding='utf-8')
            document_references = (
                DOCUMENT_REFERENCE.findall(text)
                if path.suffix.lower() in {'.xsl', '.xslt'}
                else []
            )
            for reference in document_references:
                parts = urlsplit(reference)
                if parts.scheme or parts.netloc:
                    fail(
                        f'Runtime network document() reference in '
                        f'{path.relative_to(REPOSITORY_ROOT)}: {reference}'
                    )
                target = path.parent / unquote(parts.path)
                if not target.is_file():
                    fail(
                        f'Missing document() asset from {path.relative_to(REPOSITORY_ROOT)}: '
                        f'{reference}'
                    )
                checked += 1
    return checked


def scenarios(path: Path) -> dict[str, ET.Element]:
    root = ET.parse(path).getroot()
    result: dict[str, ET.Element] = {}
    for scenario in root.findall('scenario:scenario', NS):
        name = scenario.findtext('scenario:name', namespaces=NS)
        if not name:
            fail(f'Unnamed scenario in {path.relative_to(REPOSITORY_ROOT)}')
        if name in result:
            fail(f'Duplicate scenario name in {path.relative_to(REPOSITORY_ROOT)}: {name}')
        result[name] = scenario
    return result


def match_text(scenario: ET.Element) -> str:
    match = scenario.find('scenario:match', NS)
    return ''.join(match.itertext()).strip() if match is not None else ''


def locations(scenario: ET.Element) -> list[str]:
    return [
        location.text.strip()
        for location in scenario.findall('.//scenario:location', NS)
        if location.text
    ]


def check_scenario_policy() -> None:
    factur_x = scenarios(FACTUR_X_ROOT / 'scenarios.xml')
    for name in (
        'ZUGFeRD 2.5.2/Factur-X 1.09.2 - BasicWL',
        'ZUGFeRD 2.5.2/Factur-X 1.09.2 - MINIMUM ',
    ):
        if name not in factur_x or match_text(factur_x[name]) != 'false()':
            fail(f'Factur-X acceptance policy changed for {name!r}')

    generic_factur_x = factur_x.get('ZUGFeRD/Factur-X - EN16931 (CII) Generic')
    if generic_factur_x is None:
        fail('Generic Factur-X CII fallback scenario is missing')
    generic_match = match_text(generic_factur_x)
    if "not(contains(" not in generic_match or "'kosit'" not in generic_match:
        fail('Generic Factur-X CII fallback no longer excludes XRechnung identifiers')

    xrechnung = scenarios(XRECHNUNG_ROOT / 'scenarios.xml')
    xrechnung_specific = {
        name: scenario
        for name, scenario in xrechnung.items()
        if name.startswith('EN16931 XRechnung')
    }
    if len(xrechnung_specific) != 8:
        fail(f'Expected 8 XRechnung-specific scenarios, found {len(xrechnung_specific)}')
    for name, scenario in xrechnung_specific.items():
        if any('resources/en16931/' in location for location in locations(scenario)):
            fail(f'XRechnung-specific scenario unexpectedly uses generic EN16931 rules: {name}')

    for name in ('EN16931 (UBL Invoice)', 'EN16931 (UBL CreditNote)'):
        scenario = xrechnung.get(name)
        if scenario is None:
            fail(f'Missing generic EN16931 scenario: {name}')
        rule_locations = [location for location in locations(scenario) if 'EN16931' in location]
        expected = [GENERIC_UBL_ACTIVE]
        if rule_locations != expected:
            fail(f'Unexpected generic EN16931 rules for {name}: {rule_locations}')

    generic_cii = xrechnung.get('EN16931 (CII)')
    if generic_cii is None or match_text(generic_cii) != 'false()':
        fail('Generic XRechnung CII scenario must remain disabled to avoid ambiguous matching')


def check_factur_x_hashes_and_canaries() -> None:
    if sha256(FACTUR_X_RULE_ID_MAP) != '4e6d7c5fee2b9d749135d3d695b0a250b35b65c651ac785a99bf9af01a11bee6':
        fail('Pinned Factur-X rule ID map changed')

    schema_root = FACTUR_X_ROOT / 'Schema/factur-x-1.09.2'
    for profile, expected_hashes in FACTUR_X_HASHES.items():
        schematron_name, xslt_name = FACTUR_X_FILES[profile]
        schematron = schema_root / profile / schematron_name
        xslt = schema_root / profile / xslt_name
        codelist = schematron.with_name(f'{schematron.stem}_codedb.xml')
        actual_hashes = (sha256(schematron), sha256(xslt), sha256(codelist))
        if actual_hashes != expected_hashes:
            fail(f'Pinned Factur-X artefact changed for {profile}: {actual_hashes}')
        if b'BR-FX-EN-04' in schematron.read_bytes() or b'BR-FX-EN-04' in xslt.read_bytes():
            fail(f'Stale BR-FX-EN-04 rule returned in {profile}')

        source_rules = ET.parse(schematron).getroot()
        compiled_rules = ET.parse(xslt).getroot()
        source_assertion_ids = [
            element.get('id')
            for element in source_rules.iter()
            if local_name(element.tag) == 'assert'
        ]
        compiled_assertion_ids = [
            element.findtext('{http://www.w3.org/1999/XSL/Transform}attribute[@name="id"]')
            for element in compiled_rules.iter('{http://purl.oclc.org/dsdl/svrl}failed-assert')
        ]
        if source_assertion_ids != compiled_assertion_ids:
            fail(f'Native Factur-X assertion IDs changed during compilation for {profile}')
        source_reports = [
            element for element in source_rules.iter() if local_name(element.tag) == 'report'
        ]
        compiled_reports = list(compiled_rules.iter('{http://purl.oclc.org/dsdl/svrl}successful-report'))
        if len(source_reports) != len(compiled_reports):
            fail(f'Factur-X report count changed during compilation for {profile}')
        if any(
            not re.fullmatch(r'FX-SCH-R-[0-9a-f]{20}', report.get('id', ''))
            for report in compiled_reports
        ):
            fail(f'Factur-X report lacks its deterministic KoSIT-compatible ID for {profile}')

        for reference in DOCUMENT_REFERENCE.findall(xslt.read_text(encoding='utf-8')):
            runtime_codelist = xslt.parent / reference
            if not runtime_codelist.is_file():
                fail(f'Missing Factur-X runtime codelist for {profile}: {reference}')
            if sha256(runtime_codelist) != expected_hashes[2]:
                fail(f'Pinned Factur-X runtime codelist changed for {profile}: {reference}')

    extended_dir = schema_root / '4_Factur-X_1.09.2_EXTENDED'
    for path in (
        extended_dir / 'FACTUR-X_EXTENDED.sch',
        extended_dir / '_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt',
    ):
        content = path.read_text(encoding='utf-8')
        if "not(ram:AssociatedDocumentLineDocument/ram:LineStatusReasonCode)" not in content:
            fail(f'X20 line-status canary predicate is missing from {path.relative_to(REPOSITORY_ROOT)}')
        if "ram:LineStatusReasonCode = 'DETAIL'" not in content:
            fail(f'X20 DETAIL predicate is missing from {path.relative_to(REPOSITORY_ROOT)}')


def check_rule_release_boundaries() -> None:
    schema_root = FACTUR_X_ROOT / 'Schema/factur-x-1.09.2'
    factur_x_profiles = {
        '0_Factur-X_1.09.2_MINIMUM': (False, False),
        '1_Factur-X_1.09.2_BASICWL': (False, False),
        '2_Factur-X_1.09.2_BASIC': (False, False),
        '3_Factur-X_1.09.2_EN16931': (False, False),
        '4_Factur-X_1.09.2_EXTENDED': (True, False),
    }
    for profile, (expects_br_co_25, expects_br_co_27) in factur_x_profiles.items():
        schematron_name, _ = FACTUR_X_FILES[profile]
        root = ET.parse(schema_root / profile / schematron_name).getroot()
        rules = [element for element in root.iter() if local_name(element.tag) == 'rule']
        br_co_25_rules = [
            rule for rule in rules if '[BR-CO-25]' in ''.join(rule.itertext())
        ]
        br_co_27_rules = [
            rule for rule in rules if '[BR-CO-27]' in ''.join(rule.itertext())
        ]
        if len(br_co_25_rules) != int(expects_br_co_25):
            fail(f'Unexpected BR-CO-25 presence in Factur-X profile {profile}')
        if len(br_co_27_rules) != int(expects_br_co_27):
            fail(f'Unexpected BR-CO-27 presence in Factur-X profile {profile}')

    generic_ubl = (
        XRECHNUNG_ROOT
        / GENERIC_UBL_ACTIVE
    ).read_text(encoding='utf-8')
    for removed_rule in ('BR-CO-25', 'BR-CO-27'):
        if removed_rule in generic_ubl:
            fail(f'Generic EN16931 1.3.17 UBL unexpectedly contains {removed_rule}')

    for relative in ('EN16931-UBL-validation.xsl', 'EN16931-CII-validation.xsl'):
        bundled = (XRECHNUNG_ROOT / relative).read_text(encoding='utf-8')
        for removed_rule in ('BR-CO-25', 'BR-CO-27'):
            if removed_rule in bundled:
                fail(f'XRechnung-bundled EN16931 1.3.16 unexpectedly contains {removed_rule} in {relative}')


def check_generic_ubl_correction() -> None:
    original = XRECHNUNG_ROOT / GENERIC_UBL_SOURCE
    corrected = XRECHNUNG_ROOT / GENERIC_UBL_ACTIVE
    if sha256(original) != 'fc4e6cfa8596bba0c2abd19038a98960c6ee9fc1f44566787c115efd4f4aca7c':
        fail('Official EN16931 UBL 1.3.17 original changed')
    if sha256(corrected) != 'f8e2e46cac791bfa9b3886528f21221161425e62148dc46a66c517aa64de72ee':
        fail('Reviewed EN16931 UBL EL correction changed')
    content = corrected.read_bytes()
    if content.count(b' EG EH EL ER ') != 2 or content.replace(b' EG EH EL ER ', b' EG EH ER ') != original.read_bytes():
        fail('EN16931 UBL correction must only restore EL in both BR-CO-09 predicates')


def corpus_tree_hash(paths: list[Path]) -> str:
    inventory = ''.join(
        f'{sha256(path)}  {path.relative_to(XRECHNUNG_CORPUS_ROOT).as_posix()}\n'
        for path in sorted(paths)
    )
    return hashlib.sha256(inventory.encode('utf-8')).hexdigest()


def check_corpus_inventory() -> tuple[int, int]:
    xrechnung_files = sorted(XRECHNUNG_CORPUS_ROOT.rglob('*.xml'))
    historical = [
        path
        for path in xrechnung_files
        if path.parent == XRECHNUNG_CORPUS_ROOT / 'technical-cases'
    ]
    previous_release = [
        path
        for path in xrechnung_files
        if path.is_relative_to(XRECHNUNG_CORPUS_ROOT / 'historical/2026-01-31')
    ]
    current = [
        path for path in xrechnung_files
        if path not in historical and path not in previous_release
    ]

    if len(current) != 86:
        fail(f'Expected 86 current XRechnung instances, found {len(current)}')
    if corpus_tree_hash(current) != 'ea3767fae32813246fff1265349b26e1a963f73f52c5a29427e9ad8d530b357c':
        fail('Current XRechnung v2026-08-31 corpus tree differs from its pinned inventory')

    if len(previous_release) != 78:
        fail(f'Expected 78 preserved January 2026 instances, found {len(previous_release)}')
    if corpus_tree_hash(previous_release) != 'aa3a8d81abf74bf799a13d6f09fc897f6c36159282de7296077326e1ffffc0fa':
        fail('Historical XRechnung v2026-01-31 corpus differs from its pinned inventory')

    if len(historical) != 12:
        fail(f'Expected 12 preserved historical technical cases, found {len(historical)}')
    if corpus_tree_hash(historical) != '823ffb4e1d59ec3d7b3f6e5ec6d00fec8deefe7995bc10ba8ccc987d1ad92f10':
        fail('Historical XRechnung technical-case tree differs from its pinned inventory')

    positive_count = len(list((REPOSITORY_ROOT / 'test-data/valid-files').rglob('*.xml')))
    negative_count = len(list((REPOSITORY_ROOT / 'test-data/invalid-files').rglob('*.xml')))
    if positive_count != 399 or negative_count != 12:
        fail(
            f'Unexpected API corpus size: {positive_count} positive, {negative_count} negative'
        )
    return positive_count, negative_count


def main() -> int:
    try:
        parsed = parse_xml_assets()
        references = check_offline_reference_closure()
        check_scenario_policy()
        check_factur_x_hashes_and_canaries()
        check_rule_release_boundaries()
        check_generic_ubl_correction()
        positive_count, negative_count = check_corpus_inventory()
    except (AssertionError, OSError) as error:
        print(f'Configuration check failed: {error}', file=sys.stderr)
        return 1

    print(
        f'Configuration check passed: {parsed} XML assets, {references} offline references, '
        f'{positive_count} positive and {negative_count} negative API cases.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
