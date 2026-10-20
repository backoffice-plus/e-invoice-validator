# XRechnung 3.0.2 validator configuration provenance

## Official bundle

- KoSIT release: [`v2026-08-31`](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/tag/v2026-08-31), published on 2026-09-02.
- Upstream commit: `b436fc4bf05ad501ab5cbb4a53fdffee3d4e18be`.
- Archive: [`xrechnung-3.0.2-validator-configuration-2026-08-31.zip`](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/v2026-08-31/xrechnung-3.0.2-validator-configuration-2026-08-31.zip).
- Archive SHA-256: `2530cd107c414511c5d0462ec10f886910395abfca820db82e83d70bf01221a8`.
- XRechnung Schematron: 2.6.0.
- EN 16931 rules bundled by KoSIT for XRechnung scenarios: 1.3.16.
- Validator version used by the official configuration: KoSIT Validator 1.6.3.

All bundle files are unmodified except `scenarios.xml`. The local scenario changes below preserve this service's acceptance policy. The unresolved upstream metadata placeholder `@xrechnung.cvd.version.major.minor@` is replaced with the actual CVD version `0.9`.

The CII XRechnung scenarios retain KoSIT's new severity overrides: `CII-SR-465` and `CII-SR-466` are errors, while `CII-SR-475` and `CII-SR-476` are informational because EN 16931 1.3.16 uses incorrect contexts for them. XRechnung Schematron supplies the replacement checks `BR-TMP-4` and `BR-TMP-5`. These overrides belong to the official bundle and must remain with its bundled CEN rules.

## Generic EN 16931 UBL update

The two generic UBL scenarios use the newer EN 16931 validation artefacts 1.3.17, published on 2026-10-12:

- Upstream tag: [`validation-1.3.17`](https://github.com/ConnectingEurope/eInvoicing-EN16931/releases/tag/validation-1.3.17).
- Upstream commit: `6e35e0ab8b09eb183f7d84b282e24ef95f9f5715`.
- Archive: [`en16931-ubl-1.3.17.zip`](https://github.com/ConnectingEurope/eInvoicing-EN16931/releases/download/validation-1.3.17/en16931-ubl-1.3.17.zip).
- Archive SHA-256: `bf02a0e3f6cbe692a4a28e70be7bdcaded5612b4169b543e13d6cb4f33c29e92`.
- Vendored `EN16931-UBL-validation.xslt` SHA-256: `fc4e6cfa8596bba0c2abd19038a98960c6ee9fc1f44566787c115efd4f4aca7c`.

### Narrow Greek VAT-prefix correction

The official 1.3.17 UBL `BR-CO-09` predicate accidentally omits `EL` from its allowed prefix tokens, although its unchanged assertion text explicitly permits Greece to use `EL`. Version 1.3.16 includes that exception. A scoped runtime probe with Saxon HE 12.9 from KoSIT 1.6.3 confirmed that `EL123456789` produces one `BR-CO-09` failure in the original 1.3.17, while `GR123456789` produces none; both prefixes pass that rule in 1.3.16.

Both generic UBL scenarios therefore use the separate local derivative `resources/en16931/1.3.17/EN16931-UBL-validation-EL-corrected.xslt`, SHA-256 `f8e2e46cac791bfa9b3886528f21221161425e62148dc46a66c517aa64de72ee`. The original official XSLT above remains byte-identical and independently hash-checked. This derivative restores only the `EL` country-prefix token in the executable `BR-CO-09` predicate and its identical SVRL diagnostic predicate; no other rule, identifier, severity, message, or token is changed. The strict token matching introduced in 1.3.17 remains in force.

Run `python3 scripts/repair-en16931-ubl.py --check` to verify the derivative, or omit `--check` to regenerate it from the pinned original. The helper verifies the original and derivative SHA-256 hashes and compares the complete XML trees after reversing exactly the two predicate changes. It performs lexical byte replacement so XPath namespace declarations remain intact. The configuration checker additionally verifies both hashes and that reversing the two inserted tokens restores every original byte. The 1,140 unchanged official CEN fragment cases run against this active corrected UBL derivative; dedicated full-invoice API canaries cover both Greek prefixes and an EL credit note.

The XRechnung CIUS, Extension, and CVD scenarios deliberately remain on KoSIT's bundled EN 16931 1.3.16 rules. Both bundled CEN syntaxes and the generic UBL 1.3.17 validator omit `BR-CO-25` and `BR-CO-27`; their absence reflects the respective official release artefacts. The generic CII scenario is disabled because the active Factur-X/ZUGFeRD configuration owns the exact generic EN 16931 CII identifier. No EN 16931 1.3.17 CII validator is active in this bundle.

All resources are vendored and validation is offline at runtime. The previous 2026-01-31 configuration remains in the repository for regression comparisons.
