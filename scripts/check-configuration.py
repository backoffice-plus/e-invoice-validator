#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FACTUR_X_ROOT = REPOSITORY_ROOT / 'configuration/factur-x/1.09'
XRECHNUNG_ROOT = REPOSITORY_ROOT / 'configuration/xrechnung/3.0.2_2026-01-31'
XRECHNUNG_CORPUS_ROOT = REPOSITORY_ROOT / 'test-data/valid-files/xrechnung-3.0.2'
FACTUR_X_RULE_ID_MAP = REPOSITORY_ROOT / 'tools/factur-x-xslt/rule-id-map.json'
XML_SUFFIXES = {'.xml', '.xsd', '.xsl', '.xslt', '.sch'}
DOCUMENT_REFERENCE = re.compile(r'''document\(\s*['\"]([^'\"]+)['\"]\s*\)''')
SCENARIO_NAMESPACE = 'http://www.xoev.de/de/validator/framework/1/scenarios'
NS = {'scenario': SCENARIO_NAMESPACE}

FACTUR_X_HASHES = {
    '0_Factur-X_1.09_MINIMUM': (
        'e7e37df83337e16b50a36aa10d6dddd0456a2d1fa6c88c8f72f074036ca04abb',
        'b4710f05afe3ca2d4c4a073343067e21340b4756bb9b1f17bba6fa41d83fcc99',
    ),
    '1_Factur-X_1.09_BASICWL': (
        '86fdfac6f367b3469a5773ba4fc5a475653e94dd979fbdee7e74c20c70218308',
        'e8b142cbd8ce5c9e6a762f86180ca92167304c0c4b38b67c0da8365466b7dbea',
    ),
    '2_Factur-X_1.09_BASIC': (
        '2fe8e6019b8528b30a0918c1ceba863b1d64ce5789fa734139ad4b427c62ddc9',
        '5b4ee1fc7dfd8182f09231011e8cf3b83b5409fdde772660061dc7f0e368b43b',
    ),
    '3_Factur-X_1.09_EN16931': (
        '138524ed14f57a64315b6c56aace90408c7d10c30d86cfb0487b3c1c90300dcb',
        'd669c47e39dc30e22803ebcf2b26b3cc6da8590b3806c72f6afb91aacb3cdfe7',
    ),
    '4_Factur-X_1.09_EXTENDED': (
        '00d2df0e36b3588b49d61b0ebaab56f314e168367ebcf5157de117ac336fe86a',
        '18b3213be6481e01b5e9c02332b7127b30f68130785da81ef3d747c0adbef6c4',
    ),
}

FACTUR_X_FILES = {
    '0_Factur-X_1.09_MINIMUM': ('Factur-X_1.09_MINIMUM.sch', '_XSLT_MINIMUM/FACTUR-X_MINIMUM.xslt'),
    '1_Factur-X_1.09_BASICWL': ('Factur-X_1.09_BASICWL.sch', '_XSLT_BASIC-WL/FACTUR-X_BASIC-WL.xslt'),
    '2_Factur-X_1.09_BASIC': ('Factur-X_1.09_BASIC.sch', '_XSLT_BASIC/FACTUR-X_BASIC.xslt'),
    '3_Factur-X_1.09_EN16931': ('Factur-X_1.09_EN16931.sch', '_XSLT_EN16931/FACTUR-X_EN16931.xslt'),
    '4_Factur-X_1.09_EXTENDED': ('Factur-X_1.09_EXTENDED.sch', '_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt'),
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
        'ZUGFeRD 2.5/Factur-X 1.09 - BasicWL',
        'ZUGFeRD 2.5/Factur-X 1.09 - MINIMUM ',
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
        if any('1.3.16' in location for location in locations(scenario)):
            fail(f'XRechnung-specific scenario unexpectedly uses EN16931 1.3.16: {name}')

    for name in ('EN16931 (UBL Invoice)', 'EN16931 (UBL CreditNote)'):
        scenario = xrechnung.get(name)
        if scenario is None:
            fail(f'Missing generic EN16931 scenario: {name}')
        rule_locations = [location for location in locations(scenario) if 'EN16931' in location]
        expected = ['resources/en16931/1.3.16/EN16931-UBL-validation.xslt']
        if rule_locations != expected:
            fail(f'Unexpected generic EN16931 rules for {name}: {rule_locations}')

    generic_cii = xrechnung.get('EN16931 (CII)')
    if generic_cii is None or match_text(generic_cii) != 'false()':
        fail('Generic XRechnung CII scenario must remain disabled to avoid ambiguous matching')


def check_factur_x_hashes_and_canaries() -> None:
    if sha256(FACTUR_X_RULE_ID_MAP) != '4e6d7c5fee2b9d749135d3d695b0a250b35b65c651ac785a99bf9af01a11bee6':
        fail('Pinned Factur-X rule ID map changed')

    schema_root = FACTUR_X_ROOT / 'Schema/factur-x-1.09'
    for profile, expected_hashes in FACTUR_X_HASHES.items():
        schematron_name, xslt_name = FACTUR_X_FILES[profile]
        schematron = schema_root / profile / schematron_name
        xslt = schema_root / profile / xslt_name
        actual_hashes = (sha256(schematron), sha256(xslt))
        if actual_hashes != expected_hashes:
            fail(f'Pinned Factur-X artefact changed for {profile}: {actual_hashes}')
        if b'BR-FX-EN-04' in schematron.read_bytes() or b'BR-FX-EN-04' in xslt.read_bytes():
            fail(f'Stale BR-FX-EN-04 rule returned in {profile}')

        for reference in DOCUMENT_REFERENCE.findall(xslt.read_text(encoding='utf-8')):
            runtime_codelist = xslt.parent / reference
            if not runtime_codelist.is_file():
                fail(f'Missing Factur-X runtime codelist for {profile}: {reference}')

    extended_dir = schema_root / '4_Factur-X_1.09_EXTENDED'
    for path in (
        extended_dir / 'Factur-X_1.09_EXTENDED.sch',
        extended_dir / '_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt',
    ):
        content = path.read_text(encoding='utf-8')
        if "not(ram:AssociatedDocumentLineDocument/ram:LineStatusReasonCode)" not in content:
            fail(f'X20 line-status canary predicate is missing from {path.relative_to(REPOSITORY_ROOT)}')
        if "ram:LineStatusReasonCode = 'DETAIL'" not in content:
            fail(f'X20 DETAIL predicate is missing from {path.relative_to(REPOSITORY_ROOT)}')


def check_rule_release_boundaries() -> None:
    schema_root = FACTUR_X_ROOT / 'Schema/factur-x-1.09'
    factur_x_profiles = {
        '0_Factur-X_1.09_MINIMUM': (False, False),
        '1_Factur-X_1.09_BASICWL': (False, True),
        '2_Factur-X_1.09_BASIC': (False, True),
        '3_Factur-X_1.09_EN16931': (False, True),
        '4_Factur-X_1.09_EXTENDED': (True, True),
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
        if br_co_27_rules:
            rule = br_co_27_rules[0]
            context = rule.attrib.get('context', '')
            assertion = next(
                child
                for child in rule
                if local_name(child.tag) == 'assert'
                and '[BR-CO-27]' in ''.join(child.itertext())
            )
            predicate = assertion.attrib.get('test', '')
            if "tokenize('30 58', '\\s')" not in context or '49 59' in context:
                fail(f'Factur-X BR-CO-27 payment-code context changed in {profile}')
            if not all(
                fragment in predicate
                for fragment in ('ram:IBANID', 'ram:ProprietaryID', 'and not(')
            ):
                fail(f'Factur-X BR-CO-27 XOR predicate changed in {profile}')

    generic_ubl = (
        XRECHNUNG_ROOT
        / 'resources/en16931/1.3.16/EN16931-UBL-validation.xslt'
    ).read_text(encoding='utf-8')
    for removed_rule in ('BR-CO-25', 'BR-CO-27'):
        if removed_rule in generic_ubl:
            fail(f'Generic EN16931 1.3.16 UBL unexpectedly contains {removed_rule}')

    for relative in ('EN16931-UBL-validation.xsl', 'EN16931-CII-validation.xsl'):
        bundled = (XRECHNUNG_ROOT / relative).read_text(encoding='utf-8')
        if 'BR-CO-25' not in bundled:
            fail(f'XRechnung-bundled EN16931 1.3.15 lost BR-CO-25 in {relative}')
        if 'BR-CO-27' in bundled:
            fail(f'XRechnung-bundled EN16931 1.3.15 gained BR-CO-27 in {relative}')


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
    current = [path for path in xrechnung_files if path not in historical]

    if len(current) != 86:
        fail(f'Expected 86 current XRechnung instances, found {len(current)}')
    if corpus_tree_hash(current) != 'ffa7dbdcc170428710ef216a071a0935f2550f68864a149c8a5f7baf4574a666':
        fail('Current XRechnung v2026-01-31 corpus tree differs from its pinned inventory')

    if len(historical) != 12:
        fail(f'Expected 12 preserved historical technical cases, found {len(historical)}')
    if corpus_tree_hash(historical) != '823ffb4e1d59ec3d7b3f6e5ec6d00fec8deefe7995bc10ba8ccc987d1ad92f10':
        fail('Historical XRechnung technical-case tree differs from its pinned inventory')

    positive_count = len(list((REPOSITORY_ROOT / 'test-data/valid-files').rglob('*.xml')))
    negative_count = len(list((REPOSITORY_ROOT / 'test-data/invalid-files').rglob('*.xml')))
    if positive_count != 325 or negative_count != 8:
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
