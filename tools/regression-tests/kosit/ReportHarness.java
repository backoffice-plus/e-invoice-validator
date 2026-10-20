import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.SchemaFactory;
import net.sf.saxon.s9api.*;
import org.w3c.dom.Element;

/** Uses Saxon from the pinned production KoSIT JAR to verify original report expectations. */
public final class ReportHarness {
    static final Processor PROCESSOR = new Processor(false);
    static final String ASSERTIONS = "http://www.xoev.de/de/validator/framework/1/assertions";
    static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"")
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }

    public static void main(String[] args) throws Exception {
        switch (args[0]) {
            case "transform" -> transform(args);
            case "assertions" -> assertions(args);
            case "reports" -> reports(args);
            default -> throw new IllegalArgumentException("Unknown mode " + args[0]);
        }
    }

    static void transform(String[] args) throws Exception {
        var executable = PROCESSOR.newXsltCompiler().compile(new StreamSource(new File(args[1])));
        var transformer = executable.load();
        transformer.setSource(new StreamSource(new File(args[2])));
        transformer.setDestination(PROCESSOR.newSerializer(new File(args[3])));
        for (int i = 4; i < args.length; i++) {
            String[] pair = args[i].split("=", 2);
            transformer.setParameter(new QName(pair[0]), new XdmAtomicValue(pair[1]));
        }
        transformer.transform();
    }

    static void assertions(String[] args) throws Exception {
        var factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        var document = factory.newDocumentBuilder().parse(new File(args[1]));
        var compiler = PROCESSOR.newXPathCompiler();
        var namespaces = document.getElementsByTagNameNS(ASSERTIONS, "namespace");
        for (int i = 0; i < namespaces.getLength(); i++) {
            var element = (Element) namespaces.item(i);
            compiler.declareNamespace(element.getAttribute("prefix"), element.getTextContent().trim());
        }
        var assertions = document.getElementsByTagNameNS(ASSERTIONS, "assertion");
        var builder = PROCESSOR.newDocumentBuilder();
        try (var writer = Files.newBufferedWriter(Path.of(args[3]))) {
            for (int i = 0; i < assertions.getLength(); i++) {
                var assertion = (Element) assertions.item(i);
                String reportName = assertion.getAttribute("report-doc");
                File report = Path.of(args[2]).resolve(reportName).toFile();
                if (!report.isFile()) throw new IllegalStateException("Missing asserted report: " + report);
                String test = assertion.getAttribute("test");
                var selector = compiler.compile(test).load();
                selector.setContextItem(builder.build(new StreamSource(report)));
                boolean passed = selector.effectiveBooleanValue();
                String key = Path.of(args[1]).getFileName() + "#" + (i + 1);
                writer.write("{\"key\":" + quote(key) + ",\"report\":" + quote(reportName)
                    + ",\"test\":" + quote(test) + ",\"passed\":" + passed + "}\n");
            }
        }
    }

    static void reports(String[] args) throws Exception {
        // report.xsd imports the scenario namespace without a schemaLocation, as upstream's
        // Ant task supplies both schemas explicitly. Register that namespace first here too.
        var validator = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI)
            .newSchema(new javax.xml.transform.Source[] {
                new StreamSource(Path.of(args[1]).resolveSibling("scenarios.xsd").toFile()),
                new StreamSource(new File(args[1]))
            }).newValidator();
        var executable = PROCESSOR.newXsltCompiler().compile(new StreamSource(new File(args[2])));
        var compiler = PROCESSOR.newXPathCompiler();
        compiler.declareNamespace("svrl", "http://purl.oclc.org/dsdl/svrl");
        var failures = compiler.compile("//svrl:failed-assert");
        int checked = 0;
        for (int i = 3; i < args.length; i++) {
            try (var files = Files.list(Path.of(args[i]))) {
                for (Path path : files.filter(p -> p.toString().endsWith("-report.xml")).sorted().toList()) {
                    validator.validate(new StreamSource(path.toFile()));
                    var transformer = executable.load();
                    var destination = new XdmDestination();
                    transformer.setSource(new StreamSource(path.toFile()));
                    transformer.setDestination(destination);
                    transformer.transform();
                    var selector = failures.load();
                    selector.setContextItem(destination.getXdmNode());
                    var result = selector.evaluate();
                    if (result.size() != 0) {
                        throw new IllegalStateException("Upstream report invariants failed for " + path + ": " + result);
                    }
                    checked++;
                }
            }
        }
        System.out.println("Validated report XSD and upstream Schematron invariants: " + checked);
    }
}
