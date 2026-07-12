# XRechnung test corpus provenance

The current 86 XML documents in `standard/`, `extension/`, `technical-cases/cius/`, and `technical-cases/cvd/` are the unmodified `instances/` content from the official KoSIT XRechnung testsuite release `v2026-01-31`.

- Upstream commit: `b3791d47a2e1446b1751a27cb732aac294231293`.
- Archive: `xrechnung-3.0.2-testsuite-2026-01-31.zip`.
- Archive SHA-256: `a1e2b26d7de6db6903076d4a8548b66ca603e7b25ad17233202a73cfbfeb29ee`.

The release adds the CVD technical cases and the `03.07` standard cases that were absent from the previous local snapshot.

The 12 XML documents directly in `technical-cases/` preserve the previous repository baseline byte-for-byte. Upstream changed all 12 documents while moving their successors into `technical-cases/cius/`; retaining both generations prevents historical business and attachment cases from disappearing during the update. These legacy files remain positive API regression cases.

- Current v2026-01-31 tree: 86 files, 8,385,181 bytes, inventory SHA-256 `ffa7dbdcc170428710ef216a071a0935f2550f68864a149c8a5f7baf4574a666`.
- Preserved historical tree: 12 files, 2,202,369 bytes, inventory SHA-256 `823ffb4e1d59ec3d7b3f6e5ec6d00fec8deefe7995bc10ba8ccc987d1ad92f10`.

The inventory hashes are calculated from sorted lines in the form `<file-sha256>  <path-relative-to-this-directory>\n` and enforced by `scripts/check-configuration.py`.
