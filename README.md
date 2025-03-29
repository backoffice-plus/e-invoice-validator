# E-Invoice Validator for Germany

> [!Disclaimer]
> This tool and the information provided are offered as-is, without any guarantees or warranties. While we strive for accuracy,
>  we highly recommend verifying compliance and correctness using official documentation and sources. 

We have gathered all relevant information and packaged it into an easy-to-use, preconfigured e-invoice 
validation service, conveniently delivered as a Docker container tailored specifically for use in Germany.

This project leverages the official [KoSIT validator](https://github.com/itplr-kosit/validator) and includes multiple 
configurations to cover the range of all needed invoicing scenarios.

## Building for Local Development

For local development, you can use the Docker Compose file which builds the container from source instead of 
using the pre-built image:

```bash
docker-compose up -d
```

This will build the image locally using the Dockerfile in the current directory 
and start the validator service. As with the production setup, the validator 
API will be available at http://localhost:3010/


## Validating Documents

You can validate XRechnung and Factur-X XML-Documents using the API endpoint. 

Please note that if your Factur-X document is embedded in an PDF-File, you need to extract the xml file first from the PDF file. 
*This API does not support PDF-Files.*

```bash
curl -X POST -H "Content-Type: application/xml" --data-binary @invoice.xml http://localhost:3010/
```

### API Response Format

The API returns:
- Status code 200 for valid documents with recommendation to accept
- Status code 406 for invalid documents that should be rejected

For valid documents, the response contains one of these recommendation texts:
- "Bewertung: Es wird empfohlen das Dokument anzunehmen und weiter zu verarbeiten."
- "Bewertung: Es wird empfohlen das Dokument anzunehmen und zu verarbeiten, da die vorhandenen Fehler derzeit toleriert werden."

## Validator Test Suite

This directory includes a bash test script to validate multiple XML files against the validator API.

The current files are a set composed of [official XRechnung test corpus from KoSIT](https://github.com/itplr-kosit/xrechnung-testsuite/releases?page=1)
and example files from [FeRD](https://www.ferd-net.de/)

- Valid XML files are placed in `test-data/valid-files/`
- Invalid XML files are placed in `test-data/invalid-files/`

### Running Tests

Run the test script:

```bash
./validation-api.spec.sh
```

For verbose output, use:
```bash
./validation-api.spec.sh -v
```

The script will:
1. Find all XML files in the test directories
2. Send each file to the validator API
3. Check if the validation results match expectations
4. Display a summary of test results

### Test Script Behavior

The script validates files with the following criteria:
- Valid files should return status code 200 and contain an acceptance recommendation
- Invalid files should return status code 406

### Exit Codes

- `0`: All tests passed successfully
- `1`: Some tests failed (validation results didn't match expectations)

### Notes

- The test script assumes the validator API is available at `http://localhost:3010/`
- Files in `valid-files/` are expected to be valid XRechnung documents
- Files in `invalid-files/` are expected to be rejected

## Preconfigured scenarios and profiles for use in Germany

### XRechnung 2.0

* XRechnung 2.0.1 - EN16931 XRechnung (UBL Invoice)
* XRechnung 2.0.1 - EN16931 XRechnung Extension (UBL Invoice)
* XRechnung 2.0.1 - EN16931 XRechnung (UBL CreditNote)
* XRechnung 2.0.1 - EN16931 XRechnung (CII)

### XRechnung 2.1

* XRechnung 2.1.1 - EN16931 XRechnung (UBL Invoice)
* XRechnung 2.1.1 - EN16931 XRechnung Extension (UBL Invoice)
* XRechnung 2.1.1 - EN16931 XRechnung (UBL CreditNote)
* XRechnung 2.1.1 - EN16931 XRechnung (CII)

### XRechnung 2.2

* XRechnung 2.2.0 - EN16931 XRechnung (UBL Invoice)
* XRechnung 2.2.0 - EN16931 XRechnung Extension (UBL Invoice)
* XRechnung 2.2.0 - EN16931 XRechnung (UBL CreditNote)
* XRechnung 2.2.0 - EN16931 XRechnung (CII)
* XRechnung 2.2.0 - EN16931 XRechnung Extension (CII)

### XRechnung 2.3

* XRechnung 2.3.1 - EN16931 XRechnung (UBL Invoice)
* XRechnung 2.3.1 - EN16931 XRechnung Extension (UBL Invoice)
* XRechnung 2.3.1 - EN16931 XRechnung (UBL CreditNote)
* XRechnung 2.3.1 - EN16931 XRechnung (CII)
* XRechnung 2.3.1 - EN16931 XRechnung Extension (CII)

### XRechnung 3.0

* XRechnung 3.0.2 - EN16931 XRechnung (UBL Invoice)
* XRechnung 3.0.2 - EN16931 XRechnung Extension (UBL Invoice)
* XRechnung 3.0.2 - EN16931 XRechnung (UBL CreditNote)
* XRechnung 3.0.2 - EN16931 XRechnung (CII)
* XRechnung 3.0.2 - EN16931 XRechnung Extension (CII)

### ZUGFeRD 2.3 / Factur-X 1.07

* ZUGFeRD 2.3.2/Factur-X 1.07.2 - EN16931 (CII) Extended
* ZUGFeRD 2.3.2/Factur-X 1.07.2 - Basic
* ZUGFeRD 2.3.2/Factur-X 1.07.2 - Comfort (EN16931)

## Detailed information about supported standards

### Factur-X (ZUGFeRD)

**Factur-X** is a hybrid electronic invoice format developed by a French-German consortium, combining human-readable
PDF/A-3 documents with an embedded XML file. It complies with the European Norm EN 16931, facilitating automated processing
and easy accessibility for small to medium-sized enterprises (SMEs).

The hybrid format originally introduced in Germany as “ZUGFeRD” is technically identical to “Factur-X” — both terms 
refer to the same data structure. To emphasize its international character, this project consistently uses the term
“Factur-X”, even when referring to what was formerly known as ZUGFeRD.

#### Key Features:
- **Hybrid Format**: PDF with embedded XML
- Human and machine-readable
- Full compliance with EN 16931 requirements (exceptions: Profiles "Minimum" and "Basic WL" are not compliant)
- Designed for easy adoption by SMEs

#### Profiles Supported:

![Factur-X Profiles](images/factur-x-profiles.png)

- **MINIMUM**: Basic information only (not valid as a full invoice)
- **BASIC WL**: Header and footer information without line items (not valid as a full invoice)
- **BASIC**: Full compliance with EN 16931 requirements, including line items
- **EN 16931**: Complete European semantic standard
- **EXTENDED**: Additional fields for complex business cases, including French CTC compliance
- **XRECHNUNG**: Reference profile compatible with the German XRechnung standard

#### Further information

For detailed specifications, validation tools, and additional resources, refer to the comprehensive documentation 
provided by FNFE-MPE (French team) and [FeRD](https://www.ferd-net.de/) (German team).

### XRechnung

XRechnung is an XML-based e-invoicing format that serves as the official standard for electronic invoices in Germany, 
particularly in transactions with public sector entities. It is fully compliant with the European Norm EN 16931, 
ensuring semantic consistency and interoperability across EU member states.

It supports two different syntaxes: UBL (Universal Business Language) and CII (Cross Industry Invoice) which represent the same semantic model.

#### Key Features

- **Standards-Compliant**: Conforms to EN 16931 and the German CIUS (Core Invoice Usage Specification).
- **Dual Syntax Support**: Available in two XML syntaxes:
  - UBL (Universal Business Language)
  - CII (Cross Industry Invoice)
- **Machine-Readable**: Optimized for automated processing with structured XML data.

#### Use in B2G (Business-to-Government)

- **Legal Requirement**: Electronic invoicing using XRechnung is mandatory for suppliers to federal public authorities.
- **Submission Portals**
  - Zentrale Rechnungseingangsplattform des Bundes
  - OZG-RE – OZG-konforme Rechnungseingangsplattform der Länder und Kommunen

#### Use in B2B (Business-to-Business)

While XRechnung is primarily intended for B2G (Business-to-Government), the underlying EN 16931 standard is equally
applicable to B2B transactions. The format can be adopted voluntarily in B2B contexts where:

- Interoperability with EU partners is desired
- Automation and machine-readability of invoice data are important
- Compliance with PEPPOL or other cross-border standards is required

Many companies in regulated sectors (e.g., utilities, healthcare) are already adopting EN 16931-compliant invoices for B2B workflows.

#### ZUGFeRD Compatibility

Since version 2.2.0, the ZUGFeRD profile “XRECHNUNG” enables combining XRechnung-compliant XML with a human-readable 
PDF/A-3 container (Factur-X style). This hybrid approach is useful for B2B scenarios where a visual invoice is still expected.

#### Versions Suported

The validator supports the following validation sets from the [KoSIT XRechnung Configurations](https://github.com/itplr-kosit/validator-configuration-xrechnung) repository:

- 2.0.1 (2020-12-31)
- 2.1.1 (2021-11-15)
- 2.2.0 (2022-11-15)
- 2.3.1 (2023-05-12)
- 3.0.2 (2024-10-31)

#### Further information

- KoSIT – Official specification & tools: [xoev.de](https://www.xoev.de/)
- E-Rechnung Bund – Government e-invoicing portal: [e-rechnung-bund.de](https://www.e-rechnung-bund.de)

### Creating new scenario configurations

Here’s a concise step-by-step guide to creating a new scenario for the KoSIT Validator by following the structure of the XRechnung profile:

1. Understand the Scenario
   The scenarios.xml defines:

Namespaces for key elements.
Match Rules to identify documents by CustomizationID.
Validation Steps for XML Schema and Schematron.
Reporting Rules for validation output.

2. Gather Resources
   Collect the scenario-specific resources:

XSD files for the profile (e.g., EN16931 and ZUGFeRD-specific schemas).
Schematron (XSLT) for additional business rules.
Documentation on CustomizationID values.

3. Define Namespaces
   In the scenario, declare namespaces relevant to you scenarion, such as: `rsm: Cross-Industry Invoice (CII) namespace.`

Any additional namespaces needed for validation.

4. Match Documents Using CustomizationID
   Use the match element to identify documents based on their CustomizationID.

Example: `<match>exists(/rsm:CrossIndustryInvoice/rsm:ExchangedDocumentContext/rsm:GuidelineSpecifiedDocumentContextParameter/rsm:ID[ . = 'urn:factur-x.eu:1p0:extended'])</match>`

Replace `urn:factur-x.eu:1p0:extended` with the CustomizationID for the desired profile.

5. Add XML Schema Validation
   Include `<validateWithXmlSchema>` to ensure the document conforms to the structure defined in the XSDs:

Example:

```xml
<validateWithXmlSchema>
  <resource>
    <name>XML Schema for my Scenario</name>
    <location>path/to/my-schema.xsd</location>
  </resource>
</validateWithXmlSchema>
```

6. Add Schematron Validation
   Reference Schematron rules for additional validations:

```xml
<validateWithSchematron>
  <resource>
    <name>My Scenario Schema</name>
    <location>path/to/my-rules.xsl</location>
  </resource>
</validateWithSchematron>
```

7. Configure Reporting
   Define how validation results are reported:

```xml
<createReport>
  <resource>
    <name>Validation Report</name>
    <location>path/to/report-template.xsl</location>
  </resource>
</createReport>
```

------------------------------------------------------------

That's it. Have a happy e-invoice validation experience and focus on what really matters: solving the core problems
of your customers.

Brought to you by:

![backoffice.plus](images/backoffice.plus.png "https://backoffice.plus/")

[backoffice.plus](https://backoffice.plus/) 🚀 Digital Transformation & Automation

Contributors:

- [Karl Adler](https://www.linkedin.com/in/karl-adler-dev/), [Fudler IT-Solutions](https://fudler.de/)

- [Julian Haupt](https://www.linkedin.com/in/julian-haupt-047a853a/), [backoffice.plus](https://backoffice.plus/s)

------------------------------------------------------------
