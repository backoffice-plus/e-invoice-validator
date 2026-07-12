#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
SCHEMA_ROOT = (
    REPOSITORY_ROOT / 'configuration/factur-x/1.09/Schema/factur-x-1.09'
)
RULE_ID_MAP = TOOL_ROOT / 'rule-id-map.json'
EVENT_TAG = re.compile(r'<(?P<tag>assert|report)\b(?P<attributes>[^>]*)>')
ALLOWED_CORRIGENDUM_OVERRIDES = {
    ('FX-SCH-A-000428', 'FX-SCH-A-000421'),
    ('FX-SCH-A-000429', 'FX-SCH-A-000422'),
}


@dataclass(frozen=True)
class Profile:
    directory: str
    schematron: str
    event_count: int
    mapped_event_count: int
    identified_event_count: int


PROFILES = (
    Profile('0_Factur-X_1.09_MINIMUM', 'Factur-X_1.09_MINIMUM.sch', 107, 92, 92),
    Profile('1_Factur-X_1.09_BASICWL', 'Factur-X_1.09_BASICWL.sch', 329, 270, 270),
    Profile('2_Factur-X_1.09_BASIC', 'Factur-X_1.09_BASIC.sch', 466, 379, 379),
    Profile('3_Factur-X_1.09_EN16931', 'Factur-X_1.09_EN16931.sch', 618, 424, 424),
    Profile('4_Factur-X_1.09_EXTENDED', 'Factur-X_1.09_EXTENDED.sch', 1458, 934, 937),
)


def normalize(value: str) -> str:
    return ' '.join(value.split())


def local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def schematron_events(path: Path) -> list[ET.Element]:
    return [
        element
        for element in ET.parse(path).getroot().iter()
        if local_name(element.tag) in {'assert', 'report'}
    ]


def load_rule_ids() -> dict[str, str]:
    document = json.loads(RULE_ID_MAP.read_text(encoding='utf-8'))
    if document.get('schema_version') != 'e-invoice-validator.factur-x-rule-id-map/v1':
        raise ValueError('unexpected Factur-X rule ID map schema')
    rules = document.get('rules')
    if not isinstance(rules, dict) or len(rules) != 390:
        raise ValueError('Factur-X rule ID map must contain exactly 390 entries')
    if any(not isinstance(message, str) or not isinstance(rule_id, str) for message, rule_id in rules.items()):
        raise ValueError('invalid Factur-X rule ID map entry')
    return rules


def validate_profile(
    profile: Profile,
    events: list[ET.Element],
    rule_ids: dict[str, str],
    require_complete: bool,
) -> list[str | None]:
    if len(events) != profile.event_count:
        raise ValueError(
            f'{profile.directory}: expected {profile.event_count} assertions/reports, '
            f'found {len(events)}'
        )

    desired_ids: list[str | None] = []
    mapped = 0
    identified = 0
    for element in events:
        message = normalize(''.join(element.itertext()))
        desired = rule_ids.get(message)
        existing = element.get('id')
        desired_ids.append(desired)
        if desired:
            mapped += 1
        if existing:
            identified += 1

        if existing and desired and existing != desired:
            if (existing, desired) not in ALLOWED_CORRIGENDUM_OVERRIDES:
                raise ValueError(
                    f'{profile.directory}: rule ID mismatch {existing!r} != {desired!r} '
                    f'for {message!r}'
                )
        elif require_complete and desired and not existing:
            raise ValueError(
                f'{profile.directory}: missing rule ID {desired!r} for {message!r}'
            )

    if mapped != profile.mapped_event_count:
        raise ValueError(
            f'{profile.directory}: expected {profile.mapped_event_count} mapped events, '
            f'found {mapped}'
        )
    if require_complete and identified != profile.identified_event_count:
        raise ValueError(
            f'{profile.directory}: expected {profile.identified_event_count} identified '
            f'events, found {identified}'
        )
    return desired_ids


def enrich_source(path: Path, events: list[ET.Element], desired_ids: list[str | None]) -> int:
    source = path.read_text(encoding='utf-8')
    matches = list(EVENT_TAG.finditer(source))
    if len(matches) != len(events):
        raise ValueError(
            f'{path.relative_to(REPOSITORY_ROOT)}: lexical event count '
            f'{len(matches)} differs from parsed count {len(events)}'
        )

    replacements: list[str] = []
    cursor = 0
    changed = 0
    for match, element, desired in zip(matches, events, desired_ids, strict=True):
        replacements.append(source[cursor:match.start()])
        tag = match.group('tag')
        if tag != local_name(element.tag):
            raise ValueError(f'{path.relative_to(REPOSITORY_ROOT)}: event order changed')
        if desired and not element.get('id'):
            replacements.append(f'<{tag} id="{desired}"{match.group("attributes")}>')
            changed += 1
        else:
            replacements.append(match.group(0))
        cursor = match.end()
    replacements.append(source[cursor:])

    if changed:
        path.write_text(''.join(replacements), encoding='utf-8', newline='')
    return changed


def run(write: bool) -> int:
    rule_ids = load_rule_ids()
    changed = 0
    for profile in PROFILES:
        path = SCHEMA_ROOT / profile.directory / profile.schematron
        events = schematron_events(path)
        desired_ids = validate_profile(profile, events, rule_ids, require_complete=not write)
        if write:
            changed += enrich_source(path, events, desired_ids)
            validate_profile(
                profile,
                schematron_events(path),
                rule_ids,
                require_complete=True,
            )

    mode = 'restored' if write else 'verified'
    print(
        f'Factur-X rule IDs {mode}: {sum(profile.identified_event_count for profile in PROFILES)} '
        f'identified assertions/reports across {len(PROFILES)} profiles'
        + (f' ({changed} added).' if write else '.')
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Restore and verify stable Factur-X report rule IDs.'
    )
    parser.add_argument(
        '--write',
        action='store_true',
        help='add missing IDs to the pinned Schematron sources',
    )
    arguments = parser.parse_args()
    try:
        return run(arguments.write)
    except (ET.ParseError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f'Factur-X rule ID check failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
