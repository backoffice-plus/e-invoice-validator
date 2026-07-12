# XRechnung 3.0.2 validator configuration provenance

## Official bundle

- KoSIT release: `v2026-01-31`, commit `4b8cd64524d9af0b8b5db7d541ff7a2bf9827617`.
- Archive: `xrechnung-3.0.2-validator-configuration-2026-01-31.zip`.
- Archive SHA-256: `6a5a5911a421b25fbc423f62f93f894df7b236f5d73ca4f84bb222a945082704`.
- XRechnung Schematron: 2.5.0.
- EN 16931 rules bundled by KoSIT for XRechnung scenarios: 1.3.15.

## Generic EN 16931 UBL update

The two generic UBL scenarios use the newer EN 16931 validation artefacts 1.3.16:

- Upstream tag: `validation-1.3.16`, commit `b6c9e06a59812fb1a83585da40923b3678a649ad`.
- Archive: `en16931-ubl-1.3.16.zip`.
- Archive SHA-256: `bafada015efbc5248bf5e05ad2191e1d9833ef96e9dd5f4bce420a747342da85`.
- Vendored `EN16931-UBL-validation.xslt` SHA-256: `39f9d282867f1a49e7708d9e29a53da89643e1ee56f10cec1ebcf1277595fcbd`.

The XRechnung CIUS, Extension, and CVD scenarios deliberately remain on KoSIT's bundled EN 16931 1.3.15 rules. The generic CII scenario is disabled because the active Factur-X/ZUGFeRD configuration owns the exact generic EN 16931 CII identifier. No EN 16931 1.3.16 CII validator is active in this bundle.

All resources are vendored and validation is offline at runtime.
