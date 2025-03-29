# Factur-X 1.07.2 (ZUGFeRD 2.3.2)

**Factur-X** is a hybrid electronic invoice format developed by a French-German consortium, combining human-readable 
PDF/A-3 documents with embedded XML data. It complies with the European Norm EN 16931, facilitating automated processing 
and easy accessibility for small to medium-sized enterprises (SMEs).

## Key Features:
- Hybrid Format: PDF with embedded XML (UN/CEFACT CII D22B XML standard)
- Human and machine-readable
- Compliant with EU Directive 2014/55/EU
- Designed for easy adoption by SMEs

## Profiles Supported:

![Factur-X Profiles](/docs/factur-x profiles.png)

- **MINIMUM**: Basic information only (not valid as a full invoice under certain legal contexts)
- **BASIC WL**: Header and footer information without line items
- **BASIC**: Full compliance with EN 16931 requirements, including line items
- **EN 16931**: Complete European semantic standard
- **EXTENDED**: Additional fields for complex business cases, including French CTC compliance
- **XRECHNUNG**: Reference profile compatible with the German XRechnung standard

## Responsible Organizations:
- French team: FNFE-MPE
- German team: FeRD

For detailed specifications, validation tools, and additional resources, refer to the comprehensive documentation provided by FNFE-MPE and [FeRD](https://www.ferd-net.de/).