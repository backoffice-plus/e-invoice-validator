# Factur-X 1.09.2 / ZUGFeRD 2.5.2 provenance

This directory is a versioned, offline validation bundle. Runtime validation does not fetch external resources.

## Upstream inputs

- Standard: Factur-X 1.09.2 / ZUGFeRD 2.5.2, released 2026-08-04, effective 2026-09-01. The current release is published by [FeRD](https://www.ferd-net.de/standards/zugferd) and [FNFE-MPE](https://fnfe-mpe.org/factur-x/); the Schematron headers record both dates.
- KoSIT configuration packaging: [`LandrixSoftware/validator-configuration-zugferd`](https://github.com/LandrixSoftware/validator-configuration-zugferd), tag [`validation-configuration-zugferd-2.5.2`](https://github.com/LandrixSoftware/validator-configuration-zugferd/releases/tag/validation-configuration-zugferd-2.5.2), commit `8399f5459df34b2af9cae0d613870649b3f17a58`.
- Landrix release archive: `validation-configuration-zugferd-2.5.2-2026-10-15.zip`, SHA-256 `43487e76edad8b7276da8266f0b1473b597be23554d1ab7fb1c828a03036eafa`.
- Compiler: `com.helger.maven:ph-schematron-maven-plugin:10.2.0`, language `en`, default ISO Schematron engine.

The XML schemas, Schematron sources, source codelists, and five top-level report-path wrappers are retained unchanged from the Landrix release. All five runtime validators are regenerated from these Schematron sources with the pinned compiler.

## Pinned rules

| Profile | Schematron SHA-256 | Generated XSLT SHA-256 | Runtime codelist SHA-256 |
| --- | --- | --- | --- |
| MINIMUM | `c570a628498e0b633a3dd66dd745653a8a2bc66fc6ee346b1971b9dc2d5f6778` | `6d35419c2f10be60b8f7b035129b176e11b9c006c8d422053d0c8e25880230ec` | `5c575cf37533a12a758f08b6b9691841c1691f2af214f21e040a07ec892e1f20` |
| BASIC WL | `c32dd6eb4ef9c3e88772726ff86aca796476b719152edd6d95aa96ddb17a63f0` | `b5b8acca436e50086f84647d5e1ee7d4606b93dec41cfc3cfa1cb18b54c5b92b` | `a34cd66dda00a9260368fa02dad97e966ded1c1ad100787a5318074328d20abb` |
| BASIC | `b2a84cee0e497733bf595c435db18ba720a9f2e16f6741a972667a2f277f6bed` | `733e08a96db7d59827b196eb2674b764bed8e54335073e4fa05b59b99d17938e` | `a150b48359a72e1c1629edddb147d5133aabd03adb6ce8b3d287d0c2a6936d21` |
| EN 16931 | `ef8c8380b499d1267b2dcf1fa709b45631a77d6d5f220c6cc2ade2fdade59473` | `88b95d60df0c47e0c9cec15071c0583c9013bb80b2b9dc12b570c32af9af093d` | `70339a41d71b02bb97683f8eea04acbd764e077a88a446b32860d89c3351b62f` |
| EXTENDED | `5b9039e31f86e90f1a34925e84d3fad206efa3ca5639bb98a0cefd3661d3e36a` | `8aae1322ce15e127b112cf2c8c84dc61c02e95c124261da0a6f297bd3e1a1853` | `6e23aedbba0e3b32b3b1211d145186193215f56f755201555306c42327e75fbc` |

The source codelists are copied byte-for-byte beside the generated validators under their referenced `FACTUR-X_*_codedb.xml` filenames. The regeneration script verifies these runtime dependencies.

## Changes from the historical 1.09 bundle

The 1.09.2 release includes the EXTENDED `LineStatusReasonCode` corrections, including the `DETAIL`/unspecified filtering used by tax-base and monetary-total checks. The separate 1.09 corrigendum overlay is therefore no longer required. The obsolete `BR-FX-EN-04` rule remains absent. `BR-CO-27` is absent from all five profiles in this release; `BR-CO-25` remains in EXTENDED only.

All 2,094 assertions now carry upstream IDs (55 MINIMUM, 278 BASIC WL, 385 BASIC, 433 EN 16931, and 943 EXTENDED). No local assertion-ID enrichment is applied. Many report codes consequently use their native identifiers, such as `PEPPOL-EN16931-R008` and `BR-CO-16`, instead of the generated `FX-SCH-A-*` identifiers present in 1.09. The historical map remains available only for reproduction of 1.09.

The 872 upstream `<report>` rules have no IDs (11 MINIMUM, 59 BASIC WL, 87 BASIC, 194 EN 16931, and 521 EXTENDED). KoSIT's SVRL schema requires an ID on every `successful-report`; firing one of these rules otherwise causes an unsuccessful validation process and HTTP 422, despite an available rejection report. After compilation, `identify-generated-reports.py` inserts only missing IDs on the generated literal `svrl:successful-report` start tags. It leaves the Schematron sources, assertion IDs, XPath expressions, messages, and severities unchanged. This makes prohibited-element reports return an ordinary HTTP 406 rejection with an identifiable code.

Each inserted ID is `FX-SCH-R-` followed by the first 20 hexadecimal characters of SHA-256 over the UTF-8 compact JSON array `[template match context, report test, report message]`, with each string's whitespace normalized. The IDs depend on rule content, not its position. The helper checks for hash collisions and verifies that removing the inserted attributes restores the original parsed XSLT tree. Lexical insertion preserves namespace declarations referenced only by XPath expressions. Both generation and `--check` apply this deterministic metadata repair; the pinned XSLT hashes above include it. Historical Factur-X 1.09 generation is unchanged.

Compiler 10.2.0 was compared with 9.0.1 on these five sources: the generated failed-assertion IDs, tests, and severities are identical. The compiler update changes generator metadata and redundant templates, and emits `active-pattern/@documents` without the obsolete `@document` attribute; the vendored KoSIT report stylesheets do not consume either attribute.

## Local acceptance policy

`scenarios.xml` retains the service's existing policy, with its version references updated:

- MINIMUM and BASIC WL remain technically recognizable Factur-X profiles, but do not match this service because they are not complete EN 16931 invoices.
- The generic CII fallback excludes every identifier containing `kosit`, covering both historical `xoev-de:kosit` and current `xeinkauf.de:kosit` XRechnung identifiers.
- Historical Factur-X 1.07.2 and 1.09 assets remain available for regression work. The production container activates only this 1.09.2 bundle.

The configuration date is set to the Landrix packaging date, 2026-10-15.

## Reproduction

Run `scripts/regenerate-factur-x-xslt.sh --check` from the repository root. Omitting `--check` regenerates and installs all five validators and runtime codelists. The script verifies upstream assertion IDs before compilation.

Use `scripts/regenerate-factur-x-xslt.sh --version 1.09 --check` to reproduce the historical 1.09 bundle with its original compiler 9.0.1 and local ID map.
