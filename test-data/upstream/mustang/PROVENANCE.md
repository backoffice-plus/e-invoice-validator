# Mustangproject invoice corpus

These are complete upstream invoice XML documents, preserved byte-for-byte with their original directory names, comments, copyright notices, encodings and line endings.

- Repository: [ZUGFeRD/mustangproject](https://github.com/ZUGFeRD/mustangproject).
- Commit: [`d3d51fd01a6a9c1fa4401bc8c08049e3dd0d7020`](https://github.com/ZUGFeRD/mustangproject/commit/d3d51fd01a6a9c1fa4401bc8c08049e3dd0d7020), inspected on 2026-10-20.
- Archive: `https://codeload.github.com/ZUGFeRD/mustangproject/zip/d3d51fd01a6a9c1fa4401bc8c08049e3dd0d7020`.
- Archive SHA-256: `845a2bf0d4636ba68446aec99bc771817f228510655eab9df8ec2298066d227c`.
- Project license: Apache License 2.0; upstream [LICENSE](LICENSE) and [NOTICE](NOTICE) are retained. Individual fixture notices, including FeRD's embedded rights-of-use text and explicit Apache notices, are also retained verbatim.

`inventory.json` maps every imported file to its upstream path, SHA-256, document syntax, guideline identifiers and any Java test references found at the pinned commit. `SHA256SUMS` pins the 98 invoice XML files plus LICENSE and NOTICE. Expectations and explanatory metadata remain separately editable.

## Coverage

All XML resources below the upstream CLI, library and validator `src/test/resources` directories were parsed. Documents with a complete `CrossIndustryInvoice`, UBL `Invoice`, UBL `CreditNote`, or historical `CrossIndustryDocument` root were selected; Maven/configuration XML, Order-X documents, reports and other resource types were not imported.

| Syntax | Files | API coverage |
| --- | ---: | --- |
| CII `CrossIndustryInvoice` | 57 | Included |
| UBL `Invoice` | 29 | Included |
| UBL `CreditNote` | 3 | Included |
| ZUGFeRD 1.0 `CrossIndustryDocument` | 9 | Explicitly excluded |
| Total | 98 | 89 cases, 9 exclusions |

There are 96 distinct byte contents. The duplicate sub-invoice hierarchy fixture and duplicate UBL full-model snapshot retain both original source paths; both occurrences are tested. Legacy ZUGFeRD 1.0 files remain in the source inventory and in `cases.json` exclusions, without enabling a legacy runtime configuration.

## Expectations

`cases.json` contains independently reviewable expectations and pinned upstream fixture/test permalinks for every modern source. Its 44 acceptance cases and 45 rejection cases distinguish profile routing, XML-schema validation, business rules and tolerated warnings. The manifest is not generated from API responses by the importer.

The source is a mixed importer, calculator, visualizer and validator test corpus. Successful upstream import or conversion is not a claim that the source passes the current validation profile. Examples of this distinction are:

- `invalidArithmetics.xml` is explicitly accepted by upstream `testArithmetics`; its name does not make it a negative test. Empty-element warnings remain tolerated.
- `invalidSubInvoiceLineHierarchy.xml` deliberately changes a GROUP subtotal from 1050.00 to 999.00. Mustang's older expectation is a warning; the released Factur-X 1.09.2 `BR-FXEXT-08` has error severity, so rejection is expected here.
- The coffee-bundle importer sample has GROUP lines with category S and a zero VAT rate. `BR-S-05` rejects those lines under the current released rules.
- Some historical conversion inputs contain obsolete or out-of-profile schema elements. These unchanged sources are explicit schema-rejection cases, rather than being silently repaired.
- Twenty-three sources intentionally match no active scenario: MINIMUM invoices, generic UBL examples without an EN16931 CustomizationID, UBL Peppol/Factur-X customization variants without a configured validator, and malformed or incompatible CII guideline identifiers. They assert `expected_no_scenario` as well as HTTP 406.
- Historical XRechnung 2.x fixtures are tested through the corresponding configurations already activated by the service. French CTC-specific validation is not enabled; its CII fixture is rejected by the EN16931 guideline-ID rule.
- Upstream warning counts are not copied across different releases. Required warning/error codes are specified where the source and active rule provide a concrete regression assertion.

The three historical sources `validV2.xml`, `validZREtestZugferd.xml`, and `valid_with_VAT_O.xml` expose prohibited-element/attribute reports without IDs in the released Schematron. Their manifest expectation is a normal HTTP 406 rejection; generated report metadata must carry IDs so KoSIT does not convert these business-rule failures into HTTP 422.

## Reproduction

Download the pinned commit archive to a local file, then run:

```sh
python3 scripts/import-mustang-corpus.py --archive /path/to/mustangproject-pinned.zip --check
```

Omit `--check` to restore the byte-for-byte fixture files, LICENSE, NOTICE and SHA256SUMS from that verified archive. The importer neither downloads resources nor rewrites `cases.json` or `inventory.json`.

Run the API cases with `scripts/test-upstream-api.py` and this directory's `cases.json` against a container built from the active pinned configuration.
