"""Guard the report-code checks that distinguish regression failures from rejection."""

import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('upstream_api', ROOT / 'scripts/test-upstream-api.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def report(code='EXPECTED', override=''):
    return f'''<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1"
      xmlns:s="http://www.xoev.de/de/validator/framework/1/scenarios">
      <rep:scenarioMatched>
        <s:scenario><s:name>Fixture</s:name><s:createReport>{override}</s:createReport></s:scenario>
        <rep:validationStepResult><rep:message code="{code}" level="warning"/></rep:validationStepResult>
      </rep:scenarioMatched><rep:assessment><rep:reject/></rep:assessment>
    </rep:report>'''.encode()


class ApiExpectationsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.invoice = self.directory / 'invoice.xml'
        self.invoice.write_text('<Invoice/>')
        self.case = dict(id='case', path=self.invoice, expected_status=406)

    def check(self, body, **expectations):
        response = urllib.error.HTTPError('http://validator', 406, '', {}, io.BytesIO(body))
        with patch.object(runner.urllib.request, 'urlopen', side_effect=response):
            return runner.check_case(dict(self.case, **expectations), 'http://validator', 5)[1]

    def test_rejection_for_an_unrelated_rule_is_a_failure(self):
        self.assertTrue(self.check(report('OTHER'), expected_error_codes=['EXPECTED']))

    def test_custom_levels_determine_effective_error_severity(self):
        body = report(override='<s:customLevel level="error">EXPECTED</s:customLevel>')
        self.assertEqual(self.check(body, expected_error_codes=['EXPECTED']), [])
        self.assertTrue(self.check(body, expected_warning_codes=['EXPECTED']))

    def test_warning_and_forbidden_codes_are_checked(self):
        self.assertEqual(self.check(report(), expected_warning_codes=['EXPECTED']), [])
        self.assertTrue(self.check(report(), forbidden_codes=['EXPECTED']))

    def test_http_rejection_with_invalid_report_fails(self):
        self.assertTrue(self.check(b'<html>an upstream proxy error</html>'))
        self.assertTrue(self.check(b'invalid XML'))

    def test_unsupported_profile_is_distinguished_from_a_rule_rejection(self):
        self.assertTrue(self.check(report(), expected_no_scenario=True))
        unknown = b'''<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">
          <rep:noScenarioMatched/><rep:assessment><rep:reject/></rep:assessment></rep:report>'''
        self.assertEqual(self.check(unknown, expected_no_scenario=True), [])
        incomplete = b'''<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">
          <rep:assessment><rep:reject/></rep:assessment></rep:report>'''
        self.assertTrue(self.check(incomplete, expected_no_scenario=True))

    def test_processing_error_is_not_a_business_rejection(self):
        response = urllib.error.HTTPError('http://validator', 422, '', {}, io.BytesIO(report()))
        with patch.object(runner.urllib.request, 'urlopen', side_effect=response):
            errors = runner.check_case(self.case, 'http://validator', 5)[1]
        self.assertTrue(any('expected HTTP 406, got 422' in error for error in errors))

    def manifest(self, cases):
        path = self.directory / 'cases.json'
        path.write_text(json.dumps(dict(source='fixture', cases=cases)))
        return path

    def test_missing_and_duplicate_cases_fail_manifest_validation(self):
        entry = dict(id='case', file='invoice.xml', expected_status=200, rationale='upstream test')
        self.assertEqual(len(runner.load_cases([self.manifest([entry])])[0]), 1)
        with self.assertRaises(ValueError):
            runner.load_cases([self.manifest([entry, entry])])
        with self.assertRaises(ValueError):
            runner.load_cases([self.manifest([])])

    def test_fixture_coverage_detects_an_unassigned_uppercase_xml(self):
        fixture_root = self.directory / 'fixtures'
        fixture_root.mkdir()
        (fixture_root / 'invoice.xml').write_text('<Invoice/>')
        (fixture_root / 'second.XML').write_text('<Invoice/>')
        entry = dict(id='case', file='fixtures/invoice.xml', expected_status=200, rationale='upstream test')
        path = self.manifest([entry])
        document = json.loads(path.read_text())
        document['coverage'] = dict(root='fixtures', files=2, cases=1, exclusions=1)
        path.write_text(json.dumps(document))
        with self.assertRaises(ValueError):
            runner.load_cases([path])
        document['exclusions'] = [dict(file='fixtures/second.XML', reason='unsupported legacy syntax')]
        path.write_text(json.dumps(document))
        self.assertEqual(len(runner.load_cases([path])[0]), 1)


if __name__ == '__main__':
    unittest.main()
