# XRechnung test corpus provenance

The current 86 XML documents in `standard/`, `extension/`, `technical-cases/cius/`, and `technical-cases/cvd/` are the unmodified `instances/` content from the official KoSIT XRechnung testsuite release [`v2026-08-31`](https://github.com/itplr-kosit/xrechnung-testsuite/releases/tag/v2026-08-31), published on 2026-09-02.

- Upstream commit: `44c3905c69ca236aa3b94c04be1b7e9bd066ba03`.
- Archive: [`xrechnung-3.0.2-testsuite-2026-08-31.zip`](https://github.com/itplr-kosit/xrechnung-testsuite/releases/download/v2026-08-31/xrechnung-3.0.2-testsuite-2026-08-31.zip).
- Archive SHA-256: `1e81ef7563e0fa04c0e0b0631318a7e0843a3c0beb57d83ef95ac0c4a095e3d7`.

This release updates dummy IBAN values and removes syntax elements outside the EN 16931 scope from standard cases `01.21` in CII and UBL. The CVD technical cases and the `03.07` standard cases introduced in the previous local update remain included.

The 78 XML documents under `historical/2026-01-31/` preserve every changed document from the previous official testsuite release byte-for-byte at its original relative path below that directory. The remaining eight previous documents are identical to their current counterparts and remain represented once. This preserves the complete previous test coverage while exercising the latest upstream corpus as well.

- Previous upstream release: [`v2026-01-31`](https://github.com/itplr-kosit/xrechnung-testsuite/releases/tag/v2026-01-31), commit `b3791d47a2e1446b1751a27cb732aac294231293`.
- Previous archive: `xrechnung-3.0.2-testsuite-2026-01-31.zip`, SHA-256 `a1e2b26d7de6db6903076d4a8548b66ca603e7b25ad17233202a73cfbfeb29ee`.

The 12 XML documents directly in `technical-cases/` preserve the previous repository baseline byte-for-byte. Upstream changed all 12 documents while moving their successors into `technical-cases/cius/`; retaining both generations prevents historical business and attachment cases from disappearing during the update. These legacy files remain positive API regression cases.

- Current v2026-08-31 tree: 86 files, 8,384,814 bytes, inventory SHA-256 `ea3767fae32813246fff1265349b26e1a963f73f52c5a29427e9ad8d530b357c`.
- Preserved v2026-01-31 variants: 78 files, 7,477,596 bytes, inventory SHA-256 `aa3a8d81abf74bf799a13d6f09fc897f6c36159282de7296077326e1ffffc0fa`.
- Preserved older technical-case tree: 12 files, 2,202,369 bytes, inventory SHA-256 `823ffb4e1d59ec3d7b3f6e5ec6d00fec8deefe7995bc10ba8ccc987d1ad92f10`.

The inventory hashes are calculated from sorted lines in the form `<file-sha256>  <path-relative-to-this-directory>\n` and enforced by `scripts/check-configuration.py`.
