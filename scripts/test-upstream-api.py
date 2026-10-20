#!/usr/bin/env python3
"""Check full upstream invoices against the service and their declared rule IDs."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REP = '{http://www.xoev.de/de/validator/varl/1}'
SCENARIO = '{http://www.xoev.de/de/validator/framework/1/scenarios}'
CODE_FIELDS = (
    'expected_codes', 'expected_warning_codes', 'expected_error_codes',
    'forbidden_codes', 'exact_error_codes',
)


def load_cases(manifests: list[Path]) -> tuple[list[dict], int]:
    cases = []
    excluded = 0
    ids = set()
    for manifest in manifests:
        document = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(document.get('cases'), list) or not document['cases']:
            raise ValueError(f'{manifest}: a nonempty cases array is required')
        if not document.get('source'):
            raise ValueError(f'{manifest}: source is required')
        case_paths = set()
        excluded_paths = set()
        for exclusion in document.get('exclusions', []):
            if not exclusion.get('file') or not exclusion.get('reason'):
                raise ValueError(f'{manifest}: exclusions require a file and reason')
            path = (manifest.parent / exclusion['file']).resolve()
            if not path.is_relative_to(manifest.parent.resolve()) or not path.is_file():
                raise ValueError(f'{manifest}: excluded source file is missing: {exclusion["file"]}')
            if path in excluded_paths:
                raise ValueError(f'{manifest}: duplicate excluded source: {exclusion["file"]}')
            excluded_paths.add(path)
            excluded += 1
        for entry in document['cases']:
            case = dict(entry)
            case_id = f'{manifest.parent.name}/{case["id"]}'
            if case_id in ids:
                raise ValueError(f'Duplicate upstream API case: {case_id}')
            ids.add(case_id)
            path = (manifest.parent / case['file']).resolve()
            if not path.is_relative_to(manifest.parent.resolve()) or not path.is_file():
                raise ValueError(f'{case_id}: missing file or path outside corpus: {path}')
            case_paths.add(path)
            if type(case.get('expected_status')) is not int or not 100 <= case['expected_status'] < 600:
                raise ValueError(f'{case_id}: expected_status must be an HTTP status integer')
            if not case.get('rationale'):
                raise ValueError(f'{case_id}: rationale with an upstream reference is required')
            if 'expected_no_scenario' in case and type(case['expected_no_scenario']) is not bool:
                raise ValueError(f'{case_id}: expected_no_scenario must be a boolean')
            for field in CODE_FIELDS:
                if field in case and (
                    not isinstance(case[field], list)
                    or any(not isinstance(code, str) or not code for code in case[field])
                ):
                    raise ValueError(f'{case_id}: {field} must be a list of rule IDs')
            if case.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != case['sha256']:
                raise ValueError(f'{case_id}: fixture SHA-256 differs from manifest')
            case.update(id=case_id, path=path)
            cases.append(case)
        coverage = document.get('coverage')
        if coverage is not None:
            directory = (manifest.parent / coverage['root']).resolve()
            if not directory.is_relative_to(manifest.parent.resolve()) or not directory.is_dir():
                raise ValueError(f'{manifest}: missing fixture coverage directory')
            fixture_paths = {path.resolve() for path in directory.rglob('*')
                             if path.is_file() and path.suffix.lower() == '.xml'}
            if case_paths & excluded_paths:
                raise ValueError(f'{manifest}: a fixture cannot be both tested and excluded')
            if fixture_paths != case_paths | excluded_paths:
                raise ValueError(f'{manifest}: every imported XML must be assigned to a case or explicit exclusion')
            expected = (coverage['files'], coverage['cases'], coverage['exclusions'])
            actual = (len(fixture_paths), len(document['cases']), len(document.get('exclusions', [])))
            if actual != expected:
                raise ValueError(f'{manifest}: expected fixture/case/exclusion counts {expected}, got {actual}')
    if not cases:
        raise ValueError('No upstream API cases found')
    return cases, excluded


def wait_for_api(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f'{url}/server/health', timeout=min(timeout, 5)) as response:
                root = ET.fromstring(response.read())
            if any(element.tag.rsplit('}', 1)[-1] == 'status' and element.text == 'UP'
                   for element in root.iter()):
                return
        except (urllib.error.URLError, TimeoutError, ET.ParseError):
            pass
        time.sleep(1)
    raise ValueError(f'Validator API did not become ready at {url} within {timeout:g}s')


def check_case(case: dict, url: str, timeout: float) -> tuple[str, list[str]]:
    errors = []
    request = urllib.request.Request(
        url, data=case['path'].read_bytes(),
        headers={'Content-Type': 'application/xml'}, method='POST',
    )
    try:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as response:
            with response:
                status, body = response.code, response.read()
        if status != case['expected_status']:
            errors.append(f'expected HTTP {case["expected_status"]}, got {status}')
        root = ET.fromstring(body)
        if root.tag != REP + 'report':
            raise ValueError('response is not a KoSIT validation report')
        if case['expected_status'] in (200, 406):
            assessment = 'accept' if case['expected_status'] == 200 else 'reject'
            if root.find(f'{REP}assessment/{REP}{assessment}') is None:
                errors.append(f'missing {assessment} assessment')
        matched = root.find(REP + 'scenarioMatched')
        name = None
        levels = {}
        if matched is not None:
            scenario = matched.find(SCENARIO + 'scenario')
            if scenario is not None:
                name = scenario.findtext(SCENARIO + 'name')
                for element in scenario.findall(f'{SCENARIO}createReport/{SCENARIO}customLevel'):
                    levels[(element.text or '').strip()] = element.attrib['level']
        if 'expected_scenario' in case and name != case['expected_scenario']:
            errors.append(f'expected scenario {case["expected_scenario"]!r}, got {name!r}')
        if case.get('expected_no_scenario'):
            if matched is not None:
                errors.append(f'expected an unsupported-profile rejection, got scenario {name!r}')
            if root.find(REP + 'noScenarioMatched') is None:
                errors.append('missing explicit noScenarioMatched result for unsupported profile')
        messages = [element for element in root.iter() if element.tag == REP + 'message']
        codes = {element.get('code') for element in messages if element.get('code')}
        by_level = {
            level: {element.get('code') for element in messages
                    if element.get('code') and levels.get(element.get('code'), element.get('level')) == level}
            for level in ('warning', 'error', 'information')
        }
        for field, actual in (
            ('expected_codes', codes), ('expected_warning_codes', by_level['warning']),
            ('expected_error_codes', by_level['error']),
        ):
            missing = set(case.get(field, [])) - actual
            if missing:
                errors.append(f'{field} missing {sorted(missing)}; actual codes: {sorted(c for c in codes if c)}')
        forbidden = set(case.get('forbidden_codes', [])) & codes
        if forbidden:
            errors.append(f'forbidden codes reported: {sorted(forbidden)}')
        if 'exact_error_codes' in case and set(case['exact_error_codes']) != by_level['error']:
            errors.append(f'expected exact error codes {case["exact_error_codes"]}, got {sorted(by_level["error"])}')
        for code, expected in case.get('expected_code_counts', {}).items():
            actual = sum(element.get('code') == code for element in messages)
            if actual != expected:
                errors.append(f'{code}: expected {expected} messages, got {actual}')
    except (OSError, ValueError, ET.ParseError) as error:
        errors.append(str(error))
    return case['id'], errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='append', type=Path)
    parser.add_argument('--api-url', default=os.environ.get('API_URL', 'http://localhost:8888'))
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--readiness-timeout', type=float, default=120)
    parser.add_argument('--check', action='store_true', help='validate manifests and files without HTTP requests')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--output', type=Path, help='JSONL report path; default: a unique file under tools/regression-tests/target')
    args = parser.parse_args()
    if args.workers < 1 or args.timeout <= 0 or args.readiness_timeout <= 0:
        parser.error('workers and timeouts must be positive')
    try:
        if args.manifest:
            manifests = args.manifest
        else:
            required = ROOT / 'test-data/upstream/mustang/cases.json'
            if not required.is_file() or not json.loads(required.read_text()).get('coverage'):
                raise ValueError('The complete Mustang API manifest and fixture coverage contract are required')
            manifests = sorted((ROOT / 'test-data/upstream').glob('*/cases.json'))
        cases, excluded = load_cases(manifests)
        if args.check:
            print(f'Upstream API manifests checked: {len(cases)} cases, {excluded} documented exclusions.')
            return 0
        url = args.api_url.rstrip('/')
        wait_for_api(url, args.readiness_timeout)
        failed = 0
        output = args.output
        if output is None:
            directory = ROOT / 'tools/regression-tests/target'
            directory.mkdir(parents=True, exist_ok=True)
            descriptor, filename = tempfile.mkstemp(prefix='api-results-', suffix='.jsonl', dir=directory)
            os.close(descriptor)
            output = Path(filename)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8') as report, concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(check_case, case, url, args.timeout) for case in cases]
            for future in concurrent.futures.as_completed(futures):
                case_id, errors = future.result()
                report.write(json.dumps(dict(case=case_id, status='FAIL' if errors else 'PASS', errors=errors), ensure_ascii=False) + '\n')
                if errors:
                    failed += 1
                    print(f'FAIL {case_id}: {"; ".join(errors)}', flush=True)
                elif args.verbose:
                    print(f'PASS {case_id}', flush=True)
        print(f'Upstream API: {len(cases) - failed} passed, {failed} failed; {excluded} documented exclusions.')
        print(f'Machine-readable report: {output.resolve()}')
        return int(failed != 0)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Upstream API test error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
