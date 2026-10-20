# Official KoSIT regression sources

These files are unmodified source files from the stable releases used by the active XRechnung configuration. Each source directory contains its upstream Apache-2.0 `LICENSE` and a standard `SHA256SUMS` inventory, relative to that directory. `inventory.json` also records every imported path and digest.

| Repository | Tag | Source commit | Source archive SHA-256 |
| --- | --- | --- | --- |
| [XRechnung Schematron](https://github.com/itplr-kosit/xrechnung-schematron/tree/v2.6.0) | `v2.6.0` | `217c6cbf8ac9a99d780cefb4f044b2c2778d4744` | `895872383bd380c9edcbe4c4ff973645df68102e3a797b84cd6b80280a3dd7f9` |
| [XRechnung validator configuration](https://github.com/itplr-kosit/validator-configuration-xrechnung/tree/v2026-08-31) | `v2026-08-31` | `b436fc4bf05ad501ab5cbb4a53fdffee3d4e18be` | `e4a8f51f2c691a612fcf76f3ccadc5ea933da958e196dc732b35aa97623be9e1` |

Source archives were downloaded from `https://codeload.github.com/itplr-kosit/<repository>/tar.gz/refs/tags/<tag>`. Both releases were published on 2026-09-02. Imports were verified on 2026-10-20.

## Included coverage

- `xrechnung-schematron/2.6.0/test/instances/`: all 354 XML mutation templates, comprising 128 CII, 133 UBL Invoice and 93 UBL CreditNote documents. They contain 1,108 active XML-Mutate processing instructions. Commented instructions remain inactive, matching upstream parsing.
- `validator-configuration-xrechnung/2026-08-31/src/test/cen-unit-test/`: all 33 CEN rule-test documents, including 76 active mutation instructions. Documents without mutation instructions are still validated as complete invoices by the integration run.
- `src/test/integration/`: all seven integration invoices. The original `assertions-integration-testing.xml` supplies 41 XPath expectations, including severity overrides, acceptance and rejection, extension MIME codes and CVD handling.
- `src/test/instances/`: all nine well-formed processing fixtures and both malformed/binary inputs. The well-formed fixtures also contain three mutation instructions.
- `src/test/unexpected/`: all six upstream future-target cases, containing 30 mutation instructions. These are explicitly separate from ordinary regression successes. Current known discrepancies are documented individually in `tools/regression-tests/kosit/known-failures.json`.
- Original report assertions, the report Schematron, SVRL checker, its positive and negative fixtures, and three synthetic report-generation inputs are included as technical tests.

The original sources retain upstream build placeholders. The runner replaces `@xrechnung.spec.id@` only in generated processing-fixture copies, exactly as upstream's `compile-test-sources` target does. Upstream's legacy 284 report assertions use a separate temporary scenario file produced by the original `create-test-scenario.xsl`; its deliberate BR-09 warning override tests report rendering. The production scenarios and deployed validation XSLTs are not modified.

## Mutation engine

The runner uses the same official XML-Mutate 0.6 binary referenced by both upstream build files:

- [Official artifact](https://projekte.kosit.org/api/v4/projects/356/packages/maven/de/kosit/xml-mutate/0.6/xml-mutate-0.6.jar).
- Artifact SHA-256: `b7cd05eb21c47e15dbb1d3ef38487aa65539b335e6d6c355015bbaf6ab573bec`.
- [Upstream project](https://projekte.kosit.org/kosit/xml-mutate).

The binary is downloaded into the ignored build cache and verified before each use; it is not redistributed in this repository. Mutations use the official framework's identity, removal, code-value and empty-element implementations. Expected valid and invalid rule IDs are evaluated independently; an invoice-level rejection is not substituted for a rule expectation. Missing rules, unexpected passes, unexercised known failures and execution errors are reported explicitly.

The mutation suites read the deployed XRechnung 2.6.0 and bundled CEN 1.3.16 XSLTs directly. They do not rebuild production rules from `.sch` sources and do not substitute the separate generic EN 16931 1.3.17 rules. XML-Mutate's compiled-XSLT pass-through is enforced by checking that the returned validation URI equals the deployed input URI. Native report and integration tests run with the pinned KoSIT Validator 1.6.3, including its own Saxon version.
