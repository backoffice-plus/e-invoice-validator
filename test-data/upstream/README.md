# Additional upstream regression corpora

These inputs supplement the historical full-invoice cases under `test-data/valid-files` and `test-data/invalid-files`. Imported source bytes are retained under their original relative paths. Each source records its upstream commit, archive hash, license, and file inventory. `scripts/check-upstream-corpus.py` verifies every imported XML/XSLT against the adjacent `SHA256SUMS` inventories.

| Directory | Test contract | Execution |
| --- | --- | --- |
| `en16931` | All 1,140 CEN 1.3.17 fragment cases, including scoped rule IDs, severities and exact occurrence counts | `scripts/test-en16931-rules.sh` |
| `kosit` | XRechnung Schematron 2.6.0 mutation definitions and validator-configuration v2026-08-31 rule, integration and processing tests | `scripts/test-kosit-rules.sh` |
| `mustang` | 89 complete CII/UBL cases with explicit HTTP status, scenario and diagnostic-code expectations; nine unsupported ZUGFeRD 1 source files documented separately | `scripts/test-upstream-api.py` |

Together with the 411 historical XML files, the HTTP suite checks 500 full-invoice cases, plus targeted generated canaries. The isolated KoSIT suites expand 1,888 mutation variants and evaluate 1,962 rule expectations. Their separate `unexpected/` suite retains 15 specifically documented upstream discrepancies as expected failures; the ordinary XRechnung and CEN mutation suites require all expectations to pass. The report tests add 41 production integration assertions, 284 upstream report assertions, report-schema/Schematron checks, and processing/SVRL technical tests. See the individual suite result files for the exact counts and outcomes.

Fragment cases are evaluated against their scoped business rules. XML-Mutate processing instructions must be executed to generate the intended variants. Complete invoices also exercise production scenario matching, XML Schema validation, acceptance policy, and HTTP responses. These contracts differ: a fragment that satisfies its target rule need not be a complete valid invoice, and an upstream document named `invalid` may intentionally be accepted with warnings.

The CEN UBL tests use the deployed generic EN 16931 1.3.17 validator. Its nine CII fragment cases use a separately pinned official 1.3.17 CII stylesheet solely for testing; production CII validation continues to use the official XRechnung and Factur-X bundles. KoSIT tests retain their own bundled CEN/XRechnung rule layers. Mustang expectations account for this service's existing supported profiles and acceptance policy.

Any known upstream discrepancy must be listed explicitly by case, reason, affected rule IDs and observed result. It must fail again in the same way to count as an expected failure. Unexpected passes and changed failures fail the suite. Unsupported formats are recorded separately with reasons; they are not counted as successful validations.

The tests run offline once their pinned Java tools are cached. They do not retrieve invoice dependencies at runtime. The first invocation may download the SHA-256-pinned KoSIT standalone JAR and the XML-Mutate tool described in the KoSIT provenance record. Build products and machine-readable result files live under `tools/regression-tests/target`.

Run the complete suite against a running service:

```sh
API_URL=http://localhost:8888 ./scripts/test-all.sh
```

The complete entry point requires Maven for the Factur-X regeneration check, in addition to the Java 21 JDK and Python 3.10+ used by the rule suites.

To run only isolated rule and mutation tests:

```sh
./scripts/test-rule-corpora.sh
```

To run the additional complete invoices only:

```sh
API_URL=http://localhost:8888 python3 scripts/test-upstream-api.py
```

`VALIDATOR_JAR=/absolute/path/validator-1.6.3-standalone.jar` selects an existing copy of the pinned KoSIT runtime. `scripts/ensure-validator.sh` verifies its SHA-256 before use. Original source licenses remain alongside each corpus; the repository's top-level license does not replace them.
