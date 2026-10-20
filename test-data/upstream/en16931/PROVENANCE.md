# Official CEN EN 16931 fragment tests, release 1.3.17

Imported from [ConnectingEurope/eInvoicing-EN16931](https://github.com/ConnectingEurope/eInvoicing-EN16931/tree/validation-1.3.17), tag `validation-1.3.17`, commit `6e35e0ab8b09eb183f7d84b282e24ef95f9f5715`.

The [source ZIP](https://codeload.github.com/ConnectingEurope/eInvoicing-EN16931/zip/refs/tags/validation-1.3.17) has SHA-256 `a646592f5ca31faa437f47c75b6dce585005d7ad191075a43a065d24acb89546`. Its ZIP comment identifies the same commit. Every imported file is preserved byte-for-byte and listed in `SHA256SUMS`, relative to this directory. `manifest.json` records the complete test inventory, the preserved upstream UBL validator hash, and the active corrected UBL validator hash.

## Imported material

| Source directory | Files | Fragment cases | Success expected | Error expected | Warning expected |
| --- | ---: | ---: | ---: | ---: | ---: |
| `test/Invoice-unit-UBL` | 206 | 915 | 450 | 464 | 1 |
| `test/CreditNote-unit-UBL` | 71 | 216 | 112 | 103 | 1 |
| `test/cii` | 2 | 9 | 4 | 5 | 0 |
| Total | 279 | 1,140 | 566 | 572 | 2 |

All 279 test XML files are included. The source `LICENSE.txt` (EUPL 1.2) and both `buildconfig-*.xml` files are also retained. These are fragments for isolated business-rule tests, rather than complete invoices accepted or rejected by the HTTP API. The source example-invoice directories are outside this import.

## Validation artefacts

- UBL Invoice and CreditNote tests use the active production generic UBL derivative at `configuration/xrechnung/3.0.2_2026-08-31/resources/en16931/1.3.17/EN16931-UBL-validation-EL-corrected.xslt`, SHA-256 `f8e2e46cac791bfa9b3886528f21221161425e62148dc46a66c517aa64de72ee`. The adjacent `EN16931-UBL-validation.xslt` remains byte-identical to `ubl/xslt/EN16931-UBL-validation.xslt` in the upstream commit, SHA-256 `fc4e6cfa8596bba0c2abd19038a98960c6ee9fc1f44566787c115efd4f4aca7c`; the runner verifies both hashes and reproduces the correction before running every case.
- The nine CII tests use the separately vendored `1.3.17/cii/xslt/EN16931-CII-validation.xslt`, SHA-256 `0757f07909938b1b297b8356ab7b66406c89f1b342325385d6a2def998c817f0`. This is the official CEN 1.3.17 CII validator, used only by this fragment test suite. The production Factur-X and XRechnung CII configuration is unchanged.
- Execution uses Saxon HE 12.9 from the SHA-pinned KoSIT Validator 1.6.3 standalone JAR. No additional Java or Python dependencies are installed. Once that JAR is available, the run uses local files exclusively.

The active UBL derivative restores the Greek VAT-prefix token `EL` omitted by the official 1.3.17 `BR-CO-09` implementation, although that rule's message still explicitly allows it and 1.3.16 accepts it. The only changes are the `EL` token in the executable predicate and its corresponding SVRL diagnostic test. `scripts/repair-en16931-ubl.py --check` verifies the original hash, derivative hash, and complete XML-tree equivalence after reversing these two changes. All 279 official test XML files and their 1,140 expectations remain unchanged. Separate API canaries exercise valid `EL`/`GR` invoices and an `EL` credit note; the original corpus contains no `EL`-prefix case. See the [configuration provenance](../../../configuration/xrechnung/3.0.2_2026-08-31/PROVENANCE.md) for the scoped runtime reproduction and exact correction boundary.

## Upstream expectation semantics

The runner reads each `<test>` and merges its assertions with the enclosing `<testSet>` assertions, as VEFA does. It applies the global/local rule scope before checking failures, maps Schematron `fatal` to VEFA `error`, preserves `warning`, and requires each expected rule to fire exactly `number` times (one when absent). A `<success>` expects no scoped failure for that rule. Out-of-scope failures caused by incomplete invoice fragments are ignored; XSD validation and production scenario matching are deliberately outside this suite.

Reference implementations are VEFA's [test-set inheritance](https://github.com/difi/vefa-validator/blob/5d4d3fed81e4a61768e51550e011b3c4af495292/validator-core/src/main/java/no/difi/vefa/validator/declaration/ValidatorTestSetDeclaration.java), [expectation matching](https://github.com/difi/vefa-validator/blob/5d4d3fed81e4a61768e51550e011b3c4af495292/validator-core/src/main/java/no/difi/vefa/validator/expectation/AbstractExpectation.java), and [SVRL severity mapping](https://github.com/difi/vefa-validator/blob/5d4d3fed81e4a61768e51550e011b3c4af495292/validator-core/src/main/resources/vefa-validator/xslt/svrl-parser.xslt).

The first complete run passed all 1,140 cases. No upstream exceptions were necessary. Any subsequently documented defect belongs in `tools/regression-tests/cen/expected-failures.json` with its case, affected rule IDs, reason, and exact observed result. Unexpected passes, changed failures, missing cases, and unused exception entries fail the suite.

Run `./scripts/test-en16931-rules.sh` from any directory, or supply a local pinned engine with `VALIDATOR_JAR=/absolute/path/validator-1.6.3-standalone.jar ./scripts/test-en16931-rules.sh`.
