# KoSIT rule and report regression suites

Run from any directory with a Java 21+ JDK and Python 3.10+:

```sh
./scripts/test-kosit-rules.sh
```

`scripts/ensure-validator.sh` supplies the SHA-256-pinned production KoSIT JAR. Set `VALIDATOR_JAR` to an existing copy; it is still hash-verified. XML-Mutate 0.6 is downloaded from the official KoSIT artifact repository on first use and cached under `tools/regression-tests/target/tools/`. `XML_MUTATE_JAR` can select an existing copy, also hash-verified. `KOSIT_TEST_CACHE_DIR` changes only the XML-Mutate cache location. No Maven dependencies are needed.

Every run writes its generated mutations, reports, individual JSON results, `summary.json` and diagnostic logs into a new `tools/regression-tests/target/kosit/run-*` directory. Supply `--output-dir /absolute/empty/directory` to choose a different artifact directory. Imported source files remain unchanged and are checked against their pinned inventory before execution.

The entry point executes all 354 official XRechnung templates, all 33 CEN rule templates and the six separate upstream future-target cases with XML-Mutate's original semantics. It verifies each declared `schematron-valid` and `schematron-invalid` rule ID against the actual deployed XSLTs, retaining generated invoices for inspection. Framework execution errors always fail the run. The source/instruction counts and processed-source counts are checked so a missing directory or zero-test run cannot succeed.

All 33 CEN base documents and seven integration invoices also run through the complete production KoSIT configuration. Original XPath assertions check exact codes, severity overrides and final assessments. Processing coverage includes the nine well-formed invoices, both malformed/binary fixtures, all three processing mutations, three synthetic report inputs and both SVRL-checker self-tests. Production reports are checked against their XML Schema and upstream report Schematron. A separate run executes the original legacy report assertions with upstream's explicit test-only BR-09 severity override.

`known-failures.json` records only individually identified upstream discrepancies. Every entry states a reason and pinned upstream source. A known failure that starts passing fails the suite and must be reviewed; an entry no longer exercised also fails. The six `unexpected/` source files are never silently skipped, and cases already fixed upstream are checked as normal passing expectations.

Sources, release commits, archive hashes and licenses are documented in `test-data/upstream/kosit/PROVENANCE.md`. Update the vendored sources, inventories and expected counts together when deliberately adopting a new upstream release.
