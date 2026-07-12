# Factur-X 1.09 / ZUGFeRD 2.5 provenance

This directory is a versioned, offline validation bundle. Runtime validation does not fetch external resources.

## Upstream inputs

- Standard: Factur-X 1.09 / ZUGFeRD 2.5, FINAL EN package dated 2026-06-10.
- KoSIT configuration packaging: [`LandrixSoftware/validator-configuration-zugferd`](https://github.com/LandrixSoftware/validator-configuration-zugferd), tag `validation-configuration-zugferd-2.5`, commit `ebe3f32fdbd0701eeba65a5a861d4c45d49cfa77`.
- Landrix release archive: `validation-configuration-zugferd-2.5-2026-07-01.zip`, SHA-256 `555195478642b304737e2b33af3bcf04ca397074646b8040205f1a74e7896f70`.
- Corrigendum baseline: [`svanteschubert/factur-x-corrigendum`](https://github.com/svanteschubert/factur-x-corrigendum), commit `afca5a1cae8a54b682d85d2d43f3c9c20832c223`.
- Regenerated-validator fix: commit `657531e4f69849fac032b11b735f85eb4b0984b1` on that repository's `fix` branch.
- Compiler: `com.helger.maven:ph-schematron-maven-plugin:9.0.1` with language `en`.

The official package archive itself was not retained in this repository. The hashes below pin every Schematron source and generated validator that can affect runtime business-rule validation.

## Pinned rules

| Profile | Upstream Schematron SHA-256 | Rule-ID-enriched Schematron SHA-256 | Generated XSLT SHA-256 |
| --- | --- | --- | --- |
| MINIMUM | `73d3c874b6ac31b84bb98773fb4d6708eae41380607365343055035f0d02bd70` | `e7e37df83337e16b50a36aa10d6dddd0456a2d1fa6c88c8f72f074036ca04abb` | `b4710f05afe3ca2d4c4a073343067e21340b4756bb9b1f17bba6fa41d83fcc99` |
| BASIC WL | `acf1878fb723cbfc30775d3f4006fbbc23540e319fbd70e2cb20ade1f487224c` | `86fdfac6f367b3469a5773ba4fc5a475653e94dd979fbdee7e74c20c70218308` | `e8b142cbd8ce5c9e6a762f86180ca92167304c0c4b38b67c0da8365466b7dbea` |
| BASIC | `e9d062e077a010ac0e2f41deac62b0378a16edfa38ccc3a73af9b50cb16f648c` | `2fe8e6019b8528b30a0918c1ceba863b1d64ce5789fa734139ad4b427c62ddc9` | `5b4ee1fc7dfd8182f09231011e8cf3b83b5409fdde772660061dc7f0e368b43b` |
| EN 16931 | `0a8856c74676c35c447660e2371d5e29d8d255418ac6bbfd2c168549f17055f0` | `138524ed14f57a64315b6c56aace90408c7d10c30d86cfb0487b3c1c90300dcb` | `d669c47e39dc30e22803ebcf2b26b3cc6da8590b3806c72f6afb91aacb3cdfe7` |
| EXTENDED corrigendum | `00d2df0e36b3588b49d61b0ebaab56f314e168367ebcf5157de117ac336fe86a` | same as upstream | `18b3213be6481e01b5e9c02332b7127b30f68130785da81ef3d747c0adbef6c4` |

MINIMUM, BASIC WL, BASIC, and EN 16931 use the FINAL EN Schematron rule expressions. EXTENDED uses the corrected source from `src/test/resources/corrigendum/FACTUR-X_EXTENDED.sch` in fix commit `657531e`.

The FINAL EN Schematron sources omit stable IDs from most assertions even though the supplied compiled validators contain them. Compiling those sources verbatim changes public report codes to `UNSPECIFIC`, turns warning-only accepted documents into HTTP 422 under KoSIT 1.6.2, and loses the identifiers needed for Rust differential testing. `tools/factur-x-xslt/rule-id-map.json` therefore pins 390 unambiguous message-to-ID mappings extracted from all five supplied validators (map SHA-256 `4e6d7c5fee2b9d749135d3d695b0a250b35b65c651ac785a99bf9af01a11bee6`). `restore-rule-ids.py` restores only ID metadata and verifies 2,102 identified assertion/report occurrences before compilation. Rule expressions and severities continue to come from the adjacent Schematron sources; stale supplied rules such as `BR-FX-EN-04` are not copied.

## Packaging corrections and local policy

The supplied packages contain precompiled validators that are not reliably derived from their adjacent Schematron sources. In particular, the supplied BASIC and EN 16931 validators contain the stale `BR-FX-EN-04` implementation, while the EXTENDED validator does not correctly handle all `LineStatusReasonCode` sub-invoice-line cases. Therefore all five runtime XSLT validators in this directory were regenerated from the pinned Schematron sources; no supplied precompiled rule XSLT is used.

Landrix adds a `Schema/factur-x-1.09` directory level and five small top-level XSLT wrappers. Those wrappers are retained only to provide human-readable paths in KoSIT reports; they import the regenerated validators listed above. The Schematron compiler preserves each source codelist filename in `document()` calls. Byte-identical copies of the five pinned source codelists therefore live under the exact names referenced beside each generated XSLT. The generator and configuration check enforce these runtime dependencies; without the first four KoSIT returns HTTP 422 when a codelist-backed rule is evaluated. The released EXTENDED runtime codelist is also stale and must be replaced by the corrigendum codelist, otherwise valid X20 and historical EXTENDED documents are rejected.

The following acceptance-policy changes are intentional and live in `scenarios.xml`:

- MINIMUM and BASIC WL remain technically recognizable Factur-X profiles, but do not match this service because they are not complete EN 16931 invoices.
- The generic CII fallback excludes every identifier containing `kosit`, covering both historical `xoev-de:kosit` and current `xeinkauf.de:kosit` XRechnung identifiers.
- Historical Factur-X 1.07.2 assets remain in the repository for regression work, but the production container activates only this 1.09 bundle.

## Reproduction

Run `scripts/regenerate-factur-x-xslt.sh --check` from the repository root. Omitting `--check` regenerates and installs the five validators from the pinned `.sch` files.
