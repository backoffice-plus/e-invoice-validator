# Historical XRechnung examples rejected by the current rules

These four XML examples originate from the repository's Factur-X 1.07.2 example corpus. They were moved byte-for-byte from the corresponding paths under `test-data/valid-files/` when upgrading the XRechnung configuration to [KoSIT v2026-08-31](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/tag/v2026-08-31).

Each document declares XRechnung 3.0 and supplies both `ram:PersonName` and `ram:DepartmentName` in the seller's `ram:DefinedTradeContact`. Both elements map to BT-41, whose maximum cardinality is one. The current official XRechnung configuration promotes `CII-SR-465` from a warning to an error, so these examples now belong in the negative regression corpus.

The upstream request to remove this rule was [closed without merging](https://github.com/ConnectingEurope/eInvoicing-EN16931/pull/471#issuecomment-4187519801). The [XRechnung explanation](https://github.com/ConnectingEurope/eInvoicing-EN16931/pull/471#issuecomment-3925864015) confirms that person and department names are alternative mappings of the same business term. The rejection follows the current official rules; the examples and rule severities are unchanged.
