#!/usr/bin/env python3
"""Verify the pinned corpus, run every upstream fragment, and enforce exact xfails."""

from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo = Path(sys.argv[1]).resolve()
    jar = Path(sys.argv[2]).resolve()
    corpus = repo / 'test-data/upstream/en16931'
    manifest = json.loads((corpus / 'manifest.json').read_text())
    imported = set()
    for line in (corpus / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        path = (corpus / relative).resolve()
        if path in imported or not path.is_relative_to(corpus):
            raise ValueError(f'Invalid or duplicate inventory path: {relative}')
        imported.add(path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f'Upstream artefact changed: {relative}: {actual}')
    source = corpus / '1.3.17'
    xmls = set((source / 'test').rglob('*.xml'))
    if not xmls <= imported or len(xmls) != manifest['files']:
        raise ValueError('The upstream XML inventory is incomplete or contains extra tests')
    ubl = repo / manifest['ubl_stylesheet']
    if hashlib.sha256(ubl.read_bytes()).hexdigest() != manifest['ubl_stylesheet_sha256']:
        raise ValueError('The active generic UBL validator differs from the reviewed EL correction')
    original_ubl = repo / manifest['ubl_upstream_stylesheet']
    if hashlib.sha256(original_ubl.read_bytes()).hexdigest() != manifest['ubl_upstream_stylesheet_sha256']:
        raise ValueError('The preserved official CEN UBL 1.3.17 original changed')
    repaired = subprocess.run(
        [sys.executable, str(repo / 'scripts/repair-en16931-ubl.py'), '--check'],
        capture_output=True, text=True,
    )
    if repaired.returncode:
        raise ValueError(repaired.stderr.strip() or repaired.stdout.strip())
    directory = repo / 'tools/regression-tests/cen'
    xfail_data = json.loads((directory / 'expected-failures.json').read_text())
    if xfail_data['release'] != manifest['release']:
        raise ValueError('Xfail metadata targets another release')
    xfails = {item['case']: item for item in xfail_data['cases']}
    if len(xfails) != len(xfail_data['cases']):
        raise ValueError('Duplicate xfail case')
    for case, item in xfails.items():
        if not item.get('reason', '').strip() or not item.get('rule_ids'):
            raise ValueError(f'Xfail requires affected rule IDs and a reason: {case}')
    target = repo / 'tools/regression-tests/target'
    target.mkdir(parents=True, exist_ok=True)
    output = target / 'cen-results.jsonl'
    command = ['java', '-cp', str(jar), str(directory / 'CenRuleRunner.java'), str(source), str(ubl), str(repo / manifest['cii_stylesheet'])]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    results = []
    seen = set()
    counts = collections.Counter()
    with output.open('w') as report:
        assert process.stdout is not None
        for line in process.stdout:
            result = json.loads(line)
            case = result['case']
            if case in seen:
                raise ValueError(f'Duplicate case result: {case}')
            seen.add(case)
            xfail = xfails.get(case)
            if result['matched']:
                status = 'XPASS' if xfail else 'PASS'
            elif xfail:
                fingerprint = {key: result.get(key) for key in ('scope', 'success', 'expected', 'actual', 'exception')}
                status = 'XFAIL' if fingerprint == xfail['observed'] else 'CHANGED_XFAIL'
                result['reason'] = xfail['reason']
                result['rule_ids'] = xfail['rule_ids']
            else:
                status = 'FAIL'
            result['status'] = status
            counts[status] += 1
            results.append(result)
            report.write(json.dumps(result, ensure_ascii=False) + '\n')
            if status != 'PASS':
                print(f'{status}: {case}: expected={result["expected"]} actual={result["actual"]}' + (f' {result["exception"]}' if 'exception' in result else ''))
    exit_code = process.wait()
    if exit_code:
        print(f'Java fragment runner failed with exit code {exit_code}', file=sys.stderr)
        return 1
    if len(results) != manifest['cases']:
        print(f'Incomplete run: expected {manifest["cases"]}, got {len(results)}', file=sys.stderr)
        return 1
    stale = set(xfails) - seen
    if stale:
        print(f'Unused xfail entries: {sorted(stale)}', file=sys.stderr)
        return 1
    set_counts = collections.Counter(result['case'].split('/')[1] for result in results)
    for folder, expected in manifest['sets'].items():
        if set_counts[folder.split('/')[1]] != expected['cases']:
            raise ValueError(f'Incorrect test count for {folder}')
        if len(list((source / folder).glob('*.xml'))) != expected['files']:
            raise ValueError(f'Incorrect XML file count for {folder}')
    expectation_counts = {
        'success_cases': sum(not result['expected'] for result in results),
        'error_cases': sum(any(key.startswith('error:') for key in result['expected']) for result in results),
        'warning_cases': sum(any(key.startswith('warning:') for key in result['expected']) for result in results),
    }
    for name, actual in expectation_counts.items():
        if actual != manifest[name]:
            raise ValueError(f'Incorrect {name}: expected {manifest[name]}, got {actual}')
    print(f'CEN EN16931 {manifest["release"]}: {len(results)} cases; ' + ', '.join(f'{key}={counts[key]}' for key in ('PASS', 'XFAIL', 'FAIL', 'XPASS', 'CHANGED_XFAIL')))
    print(f'Machine-readable report: {output}')
    return int(any(counts[status] for status in ('FAIL', 'XPASS', 'CHANGED_XFAIL')))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f'CEN rule test failed: {error}', file=sys.stderr)
        sys.exit(1)
