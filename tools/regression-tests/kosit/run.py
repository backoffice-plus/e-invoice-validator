#!/usr/bin/env python3
"""Run the pinned upstream mutation and integration suites, with strict known failures."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCES = ROOT / 'test-data/upstream/kosit'
XR = ROOT / 'configuration/xrechnung/3.0.2_2026-08-31'
SCHEMATRON = SOURCES / 'xrechnung-schematron/2.6.0'
CONFIG = SOURCES / 'validator-configuration-xrechnung/2026-08-31'
MUTATE_SHA256 = 'b7cd05eb21c47e15dbb1d3ef38487aa65539b335e6d6c355015bbaf6ab573bec'
MUTATE_URL = ('https://projekte.kosit.org/api/v4/projects/356/packages/maven/'
              'de/kosit/xml-mutate/0.6/xml-mutate-0.6.jar')
EXPECTED_VARIANTS = {
    'xrechnung-schematron': (1754, 1793),
    'cen-unit-test': (99, 134),
    'known-upstream-issues': (30, 30),
    'processing-mutations': (5, 5),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources() -> dict:
    manifest = json.loads((SOURCES / 'inventory.json').read_text())
    for source in manifest['sources']:
        directory = SOURCES / source['directory']
        for relative, expected in source['files'].items():
            path = directory / relative
            if not path.is_file() or digest(path) != expected:
                raise RuntimeError(f'Pinned upstream source changed: {path.relative_to(ROOT)}')
    return manifest


def ensure_mutate() -> Path:
    override = os.environ.get('XML_MUTATE_JAR')
    cache = Path(os.environ.get('KOSIT_TEST_CACHE_DIR',
                               str(ROOT / 'tools/regression-tests/target/tools')))
    path = Path(override).expanduser().resolve() if override else cache / 'xml-mutate-0.6.jar'
    if not path.exists():
        if override:
            raise RuntimeError(f'XML_MUTATE_JAR does not exist: {path}')
        cache.mkdir(parents=True, exist_ok=True)
        print('Downloading pinned KoSIT XML-Mutate 0.6 ...', flush=True)
        with urllib.request.urlopen(MUTATE_URL, timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != MUTATE_SHA256:
            raise RuntimeError('XML-Mutate download SHA-256 mismatch')
        path.write_bytes(data)
    if digest(path) != MUTATE_SHA256:
        raise RuntimeError(f'XML-Mutate SHA-256 mismatch: {path}')
    return path


def command(arguments: list[str], log: Path, timeout: int = 600) -> None:
    if Path(arguments[0]).name == 'java':
        arguments = [arguments[0], '-Duser.timezone=UTC', *arguments[1:]]
    with log.open('w') as output:
        result = subprocess.run(arguments, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                timeout=timeout)
    if result.returncode:
        tail = '\n'.join(log.read_text(errors='replace').splitlines()[-35:])
        raise RuntimeError(f'Command failed ({result.returncode}); log: {log}\n{tail}')


def instructions(paths: list[Path]) -> int:
    return sum(sum(1 for _, element in ET.iterparse(io.BytesIO(path.read_bytes()), events=['pi'])
                   if element.text.startswith('xmute ')) for path in paths)


def mutation_suite(name: str, paths: list[Path], expected_sources: int, expected_pis: int,
                   rules: list[str], java: str, classpath: str, output: Path,
                   known: dict, seen_known: set, source_root: Path = SOURCES) -> dict:
    if len(paths) != expected_sources or instructions(paths) != expected_pis:
        raise RuntimeError(f'{name}: upstream source/instruction inventory changed')
    directory = output / name
    directory.mkdir()
    filelist = directory / 'sources.txt'
    filelist.write_text(''.join(str(path.resolve()) + '\n' for path in paths))
    print(f'{name}: {len(paths)} source documents, {expected_pis} mutation instructions ...', flush=True)
    command([java, '-Xmx1g', '-Dlog4j.configurationFile=' + str(HERE / 'log4j2.xml'),
             '-cp', classpath, 'MutationHarness', str(source_root),
             str(directory), str(filelist), *rules], directory / 'runner.log')
    rows = [json.loads(line) for line in (directory / 'results.jsonl').read_text().splitlines()]
    sources = [row for row in rows if row['type'] == 'source']
    if len(sources) != expected_sources or len({row['source'] for row in sources}) != expected_sources:
        raise RuntimeError(f'{name}: not every source document was executed')
    errors = [row for row in rows if row['type'] == 'error']
    if errors:
        raise RuntimeError(f'{name}: mutation execution errors (never expected failures): {errors[:5]}')
    expectations = [row for row in rows if row['type'] == 'expectation']
    mutation_count = sum(row['mutations'] for row in sources)
    if (mutation_count, len(expectations)) != EXPECTED_VARIANTS[name]:
        raise RuntimeError(f'{name}: mutation/expectation coverage changed: '
                           f'{mutation_count}/{len(expectations)}, expected {EXPECTED_VARIANTS[name]}')
    failures = []
    xfails = 0
    for row in expectations:
        key = name + '/' + row['key']
        if key in known:
            seen_known.add(key)
            if row['passed']:
                failures.append('Unexpected pass; remove/review known failure: ' + key)
            elif bool(row.get('missing_rule')) != (known[key].get('failure_mode') == 'missing-rule'):
                failures.append('Known failure changed its failure mode: ' + key)
            else:
                xfails += 1
        elif not row['passed']:
            failures.append('Unexpected failed rule expectation: ' + key)
    stats = {'sources': len(sources), 'instructions': expected_pis,
             'mutations': mutation_count,
             'rule_expectations': len(expectations), 'expected_failures': xfails,
             'unexpected_failures': failures}
    print(f"{name}: {stats['mutations']} mutations, {len(expectations)} rule expectations, "
          f'{xfails} expected failures, {len(failures)} unexpected failures', flush=True)
    return stats


def generate_reports(name: str, inputs: list[Path], scenarios: Path, java: str,
                     validator: Path, output: Path) -> Path:
    """Report generation has its own basic assertions; business expectations follow below."""
    directory = output / name
    directory.mkdir()
    namespace = 'http://www.xoev.de/de/validator/framework/1/assertions'
    assertions = ET.Element(f'{{{namespace}}}assertions')
    ET.SubElement(assertions, f'{{{namespace}}}namespace', prefix='rep').text = (
        'http://www.xoev.de/de/validator/varl/1')
    for path in inputs:
        ET.SubElement(assertions, f'{{{namespace}}}assertion',
                      {'report-doc': path.stem + '-report.xml',
                       'test': 'exists(rep:report)'}).text = 'A report must be produced'
    assertion_file = directory / 'report-presence-assertions.xml'
    ET.ElementTree(assertions).write(assertion_file, encoding='utf-8', xml_declaration=True)
    command([java, '-Xmx1g', '-jar', str(validator), '-s', str(scenarios), '-r', str(XR),
             '-c', str(assertion_file), '-o', str(directory), *map(str, inputs)],
            directory / 'validator.log')
    expected = {path.stem + '-report.xml' for path in inputs}
    actual = {path.name for path in directory.glob('*-report.xml')}
    if actual != expected:
        raise RuntimeError(f'{name}: report inventory mismatch: {actual ^ expected}')
    return directory


def report_assertions(name: str, assertion_file: Path, reports: Path, java: str,
                      report_classpath: str, output: Path, known: dict, seen_known: set) -> dict:
    result_file = output / (name + '-assertions.jsonl')
    command([java, '-cp', report_classpath, 'ReportHarness', 'assertions', str(assertion_file),
             str(reports), str(result_file)], output / (name + '-assertions.log'))
    rows = [json.loads(line) for line in result_file.read_text().splitlines()]
    expected = len(ET.parse(assertion_file).getroot().findall(
        '{http://www.xoev.de/de/validator/framework/1/assertions}assertion'))
    if len(rows) != expected:
        raise RuntimeError(f'{name}: not every upstream XPath assertion was evaluated')
    failures = []
    xfails = 0
    for row in rows:
        key = name + '/' + row['key']
        if key in known:
            seen_known.add(key)
            if row['passed']:
                failures.append('Unexpected pass; remove/review known failure: ' + key)
            else:
                xfails += 1
        elif not row['passed']:
            failures.append('Unexpected failed report assertion: ' + key + ' ' + row['test'])
    print(f'{name}: {len(rows)} XPath assertions, {xfails} expected failures, '
          f'{len(failures)} unexpected failures', flush=True)
    return {'assertions': len(rows), 'expected_failures': xfails, 'unexpected_failures': failures}


def technical_reports(java: str, report_classpath: str, output: Path) -> dict:
    """The three synthetic report inputs are upstream technical cases, not invoices."""
    rep = {'r': 'http://www.xoev.de/de/validator/varl/1'}
    cases = ['processing-error-input.xml', 'processing-error-no-messages-input.xml',
             'missing-svrl-input.xml']
    for index, filename in enumerate(cases):
        source = CONFIG / 'src/test' / filename
        target = output / (filename.removesuffix('.xml') + '-synthetic-report.xml')
        command([java, '-cp', report_classpath, 'ReportHarness', 'transform',
                 str(XR / 'resources/default-report.xsl'), str(source), str(target),
                 'input-document=' + str(source)], output / (filename + '.log'))
        root = ET.parse(target).getroot()
        text = ''.join(root.itertext())
        if root.get('valid') != 'false' or root.find('r:assessment/r:reject', rep) is None:
            raise RuntimeError(f'{filename}: processing errors must produce an invalid rejection')
        if root.find('r:assessment/r:accept', rep) is not None:
            raise RuntimeError(f'{filename}: processing errors must never recommend acceptance')
        if index == 0 and not all(fragment in text for fragment in
                                  ['Verarbeitungsfehler', 'nicht vollst',
                                   'nicht automatisiert angenommen']):
            raise RuntimeError(f'{filename}: required processing-error explanation is missing')
        if index == 1 and 'weder Fehler noch Warnungen' in text:
            raise RuntimeError(f'{filename}: empty partial results must not claim conformance')
        if index == 2 and not ('PROCESSING_ERROR' in target.read_text() and 'not completed' in text):
            raise RuntimeError(f'{filename}: missing SVRL must produce PROCESSING_ERROR')
    # Exercise the upstream SVRL checker itself, including its negative self-test.
    checker = CONFIG / 'src/check-svrl.xsl'
    for mode, should_pass in [('passing', True), ('failing', False)]:
        log = output / f'svrl-self-test-{mode}.log'
        arguments = [java, '-Duser.timezone=UTC', '-cp', report_classpath, 'ReportHarness', 'transform',
                     str(checker), str(checker), str(output / f'svrl-{mode}.xml'),
                     'svrl.dir=' + (CONFIG / 'src/test/svrl' / mode).as_uri() + '/']
        with log.open('w') as stream:
            result = subprocess.run(arguments, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=60)
        text = log.read_text()
        if should_pass and result.returncode != 0:
            raise RuntimeError(f'SVRL positive self-test failed: {log}')
        if not should_pass and (result.returncode == 0 or 'Schematron validation failed' not in text):
            raise RuntimeError(f'SVRL negative self-test did not detect the failed assertion: {log}')
    print('Technical reports: 3 synthetic processing cases and 2 SVRL checker self-tests passed', flush=True)
    return {'synthetic_processing_cases': 3, 'svrl_checker_self_tests': 2,
            'unexpected_failures': []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validator-jar', required=True, type=Path)
    parser.add_argument('--output-dir', type=Path,
                        help='Keep generated invoices, reports, JSON results and logs here')
    args = parser.parse_args()
    if args.output_dir:
        output = args.output_dir.resolve()
    else:
        output_root = ROOT / 'tools/regression-tests/target/kosit'
        output_root.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='run-', dir=output_root))
    output.mkdir(parents=True, exist_ok=True)
    print(f'KoSIT regression artifacts: {output}', flush=True)
    started = time.monotonic()
    verify_sources()
    mutate = ensure_mutate()
    java_dir = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else None
    java = str(java_dir / 'java') if java_dir else shutil.which('java')
    javac = str(java_dir / 'javac') if java_dir else shutil.which('javac')
    if not java or not javac:
        raise RuntimeError('A Java 21 JDK (java and javac) is required')
    classes = output / 'classes'
    classes.mkdir()
    command([javac, '--release', '21', '-proc:none', '-cp', str(mutate), '-d', str(classes),
             str(HERE / 'MutationHarness.java')], output / 'compile.log')
    classpath = os.pathsep.join([str(classes), str(mutate)])
    command([javac, '--release', '21', '-proc:none', '-cp', str(args.validator_jar),
             '-d', str(classes), str(HERE / 'ReportHarness.java')], output / 'compile-reports.log')
    report_classpath = os.pathsep.join([str(classes), str(args.validator_jar)])
    known = json.loads((HERE / 'known-failures.json').read_text())
    for category in known.values():
        if any(not item.get('reason') or not item.get('upstream') for item in category.values()):
            raise RuntimeError('Every known failure must state a reason and upstream source')
    seen_known: set[str] = set()
    xr_rules = [f'xrubl={XR}/resources/xrechnung/3.0.2/xsl/XRechnung-UBL-validation.xsl',
                f'xrcii={XR}/resources/xrechnung/3.0.2/xsl/XRechnung-CII-validation.xsl']
    cen_rules = [f'cenubl={XR}/resources/ubl/2.1/xsl/EN16931-UBL-validation.xsl',
                 f'cencii={XR}/resources/cii/16b/xsl/EN16931-CII-validation.xsl']
    suites = {}
    suites['xrechnung-schematron'] = mutation_suite(
        'xrechnung-schematron', sorted((SCHEMATRON / 'test/instances').rglob('*.xml')),
        354, 1108, xr_rules, java, classpath, output, known['mutations'], seen_known)
    suites['cen-unit-test'] = mutation_suite(
        'cen-unit-test', sorted((CONFIG / 'src/test/cen-unit-test').glob('*.xml')),
        33, 76, xr_rules + cen_rules, java, classpath, output, known['mutations'], seen_known)
    suites['known-upstream-issues'] = mutation_suite(
        'known-upstream-issues', sorted((CONFIG / 'src/test/unexpected').glob('*.xml')),
        6, 30, xr_rules + cen_rules, java, classpath, output, known['mutations'], seen_known)
    integration_inputs = sorted((CONFIG / 'src/test/cen-unit-test').glob('*.xml')) + sorted(
        (CONFIG / 'src/test/integration').glob('*.xml'))
    if len(integration_inputs) != 40:
        raise RuntimeError('Expected all 33 CEN and 7 integration base documents')
    integration_reports = generate_reports('production-integration', integration_inputs,
                                           XR / 'scenarios.xml', java, args.validator_jar, output)
    suites['integration'] = report_assertions(
        'integration', CONFIG / 'src/test/assertions-integration-testing.xml',
        integration_reports, java, report_classpath, output,
        known['report_assertions'], seen_known)
    suites['integration']['documents'] = 40

    # Match compile-test-sources in the upstream Ant build, while preserving vendored bytes.
    prepared_root = output / 'prepared-sources'
    prepared = prepared_root / CONFIG.relative_to(SOURCES) / 'src/test/instances'
    for source in sorted((CONFIG / 'src/test/instances').rglob('*.xml')):
        target = prepared / source.relative_to(CONFIG / 'src/test/instances')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes().replace(
            b'@xrechnung.spec.id@',
            b'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0'))
    processing_inputs = sorted(prepared.rglob('*.xml'))
    if len(processing_inputs) != 11:
        raise RuntimeError('Expected all 9 well-formed and 2 malformed processing inputs')
    processing_reports = generate_reports('production-processing', processing_inputs,
                                          XR / 'scenarios.xml', java, args.validator_jar, output)
    suites['processing-mutations'] = mutation_suite(
        'processing-mutations', sorted((prepared / 'processing-valid').glob('*.xml')),
        9, 3, xr_rules + cen_rules, java, classpath, output,
        known['mutations'], seen_known, prepared_root)
    # The original legacy assertion suite explicitly exercises a BR-09 severity override.
    # Apply its original test-only XSLT in the output folder; production scenarios stay intact.
    test_scenarios = output / 'upstream-report-test-scenarios.xml'
    command([java, '-cp', report_classpath, 'ReportHarness', 'transform',
             str(CONFIG / 'src/create-test-scenario.xsl'), str(XR / 'scenarios.xml'),
             str(test_scenarios)], output / 'test-scenario.log')
    legacy_reports = generate_reports('upstream-report-tests', processing_inputs, test_scenarios,
                                      java, args.validator_jar, output)
    suites['upstream-report-assertions'] = report_assertions(
        'upstream-report-assertions', CONFIG / 'src/test/assertions.xml', legacy_reports,
        java, report_classpath, output, known['report_assertions'], seen_known)

    report_rules_dir = output / 'report-rules'
    command([java, '-cp', classpath, 'MutationHarness', '--compile-schematron',
             str(CONFIG / 'src/report.sch'), str(report_rules_dir)], output / 'compile-report-rules.log')
    report_rules = (report_rules_dir / 'compiled-path.txt').read_text()
    command([java, '-cp', report_classpath, 'ReportHarness', 'reports',
             str(XR / 'resources/xsd/report.xsd'), report_rules,
             str(integration_reports), str(processing_reports), str(legacy_reports)],
            output / 'report-invariants.log')
    suites['report-invariants'] = {'documents': 62, 'schema_and_schematron': True,
                                   'unexpected_failures': []}
    suites['technical-reports'] = technical_reports(java, report_classpath, output)
    failures = [failure for suite in suites.values() for failure in suite['unexpected_failures']]
    failures.extend('Known failure no longer exercised: ' + key
                    for key in known['mutations'] if key not in seen_known)
    failures.extend('Known report failure no longer exercised: ' + key
                    for key in known['report_assertions'] if key not in seen_known)
    summary = {'suites': suites, 'failures': failures,
               'elapsed_seconds': round(time.monotonic() - started, 2)}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for failure in failures:
        print(f'FAIL: {failure}', file=sys.stderr)
    print(f"KoSIT suites finished in {summary['elapsed_seconds']}s; summary: {output / 'summary.json'}")
    return bool(failures)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f'KoSIT regression failed: {error}', file=sys.stderr)
        sys.exit(1)
