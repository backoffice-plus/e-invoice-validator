# EN 16931 fragment regression tests

Run `./scripts/test-en16931-rules.sh`. Java 21+ and Python 3 are required. `scripts/ensure-validator.sh` resolves and verifies the pinned KoSIT 1.6.3 engine; `VALIDATOR_JAR` can select an existing copy. With the engine present, the suite runs offline.

The runner verifies the imported file hashes and production UBL stylesheet hash, then executes every case in the official CEN 1.3.17 unit-test corpus. This includes 915 UBL Invoice, 216 CreditNote, and nine CII fragments. The CII stylesheet is a test-only official CEN artefact. These scoped rule tests supplement the full HTTP invoice tests; fragments do not undergo XSD validation or production scenario selection.

`CenRuleRunner.java` emits the case path and ordinal, upstream ID, syntax, scope, expected failures, actual scoped failures, and success expectations. The ordinal gives every case a stable identity even when the source omits an `id`. Error and warning counts are exact, including the ten explicit upstream `number` attributes. `run.py` checks completeness and classifies every result. Full machine-readable results are written to `tools/regression-tests/target/cen-results.jsonl`.

`expected-failures.json` is empty because all 1,140 upstream cases pass. A future exception must include `case`, nonempty `rule_ids`, `reason`, and an `observed` object containing exactly the `scope`, `success`, `expected`, `actual`, and `exception` fields from the failing result (`exception` is null for ordinary assertion mismatches). Only that exact failure is an XFAIL. An unexpected pass or changed failure returns a nonzero exit status, as does an exception that no longer names an executed case.

The source release, license, hashes, counts, and VEFA semantics are documented in [the corpus provenance](../../../test-data/upstream/en16931/PROVENANCE.md).
