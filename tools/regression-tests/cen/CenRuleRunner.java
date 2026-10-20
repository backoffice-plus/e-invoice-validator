import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.TransformerException;
import javax.xml.transform.URIResolver;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamSource;
import net.sf.saxon.s9api.Axis;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.XdmDestination;
import net.sf.saxon.s9api.XdmNode;
import net.sf.saxon.s9api.XsltExecutable;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

/** Runs the upstream VEFA fragments against Schematron only, without XSD or scenario matching. */
@SuppressWarnings("deprecation") // KoSIT 1.6.3 pins Saxon 12.9; its URIResolver APIs cover compilation and execution.
class CenRuleRunner {
    private static final String VEFA = "http://difi.no/xsd/vefa/validator/1.0";
    private static final String SVRL = "http://purl.oclc.org/dsdl/svrl";
    private static final QName ID = new QName("id");
    private static final QName FLAG = new QName("flag");

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("Expected corpus, UBL XSLT, CII XSLT paths");
        Path corpus = Path.of(args[0]).toAbsolutePath();
        Processor processor = new Processor(false);
        processor.setConfigurationProperty(net.sf.saxon.lib.Feature.ALLOW_EXTERNAL_FUNCTIONS, false);
        processor.setConfigurationProperty(net.sf.saxon.lib.Feature.ALLOWED_PROTOCOLS, "file");
        URIResolver localOnly = (href, base) -> {
            URI uri = URI.create(base).resolve(href);
            if (!"file".equals(uri.getScheme())) throw new TransformerException("Remote resource denied: " + uri);
            return new StreamSource(Path.of(uri).toFile());
        };
        var compiler = processor.newXsltCompiler();
        compiler.setURIResolver(localOnly);
        XsltExecutable ubl = compiler.compile(new StreamSource(Path.of(args[1]).toFile()));
        XsltExecutable cii = compiler.compile(new StreamSource(Path.of(args[2]).toFile()));
        var factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        var builder = factory.newDocumentBuilder();
        List<Path> files;
        try (var paths = Files.walk(corpus.resolve("test"))) {
            files = paths.filter(p -> p.toString().endsWith(".xml")).sorted().toList();
        }
        for (Path file : files) {
            Element testSet = builder.parse(file.toFile()).getDocumentElement();
            if (!VEFA.equals(testSet.getNamespaceURI()) || !"testSet".equals(testSet.getLocalName())) {
                throw new IllegalArgumentException("Unexpected test file: " + file);
            }
            Element inherited = child(testSet, VEFA, "assert");
            int ordinal = 0;
            for (Element test : children(testSet, VEFA, "test")) {
                ordinal++;
                var result = new LinkedHashMap<String, Object>();
                result.put("case", corpus.relativize(file).toString().replace('\\', '/') + "#" + String.format("%03d", ordinal));
                result.put("upstream_id", test.getAttribute("id"));
                Set<String> scope = new LinkedHashSet<>();
                Set<String> successes = new LinkedHashSet<>();
                Map<String, Integer> expected = new TreeMap<>();
                // VEFA merges the file-level assertions into each test's assertions.
                readExpectations(child(test, VEFA, "assert"), scope, successes, expected);
                readExpectations(inherited, scope, successes, expected);
                result.put("scope", scope);
                result.put("success", successes);
                result.put("expected", expected);
                Map<String, Integer> actual = new TreeMap<>();
                result.put("actual", actual);
                try {
                    Element payload = null;
                    for (Node n = test.getFirstChild(); n != null; n = n.getNextSibling()) {
                        if (n instanceof Element element && !VEFA.equals(element.getNamespaceURI())) {
                            if (payload != null) throw new IllegalArgumentException("Multiple test fragments");
                            payload = element;
                        }
                    }
                    if (payload == null) throw new IllegalArgumentException("Missing test fragment");
                    boolean isCii = "CrossIndustryInvoice".equals(payload.getLocalName());
                    result.put("syntax", isCii ? "CII" : payload.getLocalName());
                    Document document = builder.newDocument();
                    document.appendChild(document.importNode(payload, true));
                    DOMSource source = new DOMSource(document, file.toUri().toString());
                    var transformer = (isCii ? cii : ubl).load();
                    transformer.setURIResolver(localOnly);
                    transformer.setInitialContextNode(processor.newDocumentBuilder().build(source));
                    XdmDestination destination = new XdmDestination();
                    transformer.setDestination(destination);
                    transformer.transform();
                    var assertions = destination.getXdmNode().axisIterator(Axis.DESCENDANT);
                    while (assertions.hasNext()) {
                        XdmNode assertion = assertions.next();
                        QName name = assertion.getNodeName();
                        if (name == null || !SVRL.equals(name.getNamespaceURI()) || !"failed-assert".equals(name.getLocalName())) continue;
                        String id = assertion.getAttributeValue(ID);
                        if (!scope.isEmpty() && !scope.contains(id)) continue;
                        // VEFA's SVRL adapter maps Schematron fatal to error, and preserves warning.
                        String flag = assertion.getAttributeValue(FLAG);
                        String severity = flag == null || "fatal".equals(flag) ? "error" : "warning".equals(flag) ? "warning" : "unknown";
                        actual.merge(severity + ":" + id, 1, Integer::sum);
                    }
                    boolean matched = expected.equals(actual);
                    for (String id : successes) {
                        if (actual.keySet().stream().anyMatch(key -> key.endsWith(":" + id))) matched = false;
                    }
                    result.put("matched", matched);
                } catch (Exception error) {
                    result.put("matched", false);
                    result.put("exception", error.getClass().getSimpleName() + ": " + error.getMessage());
                }
                System.out.println(json(result));
            }
        }
    }

    private static void readExpectations(Element assertion, Set<String> scope, Set<String> success, Map<String, Integer> expected) {
        if (assertion == null) return;
        for (Node n = assertion.getFirstChild(); n != null; n = n.getNextSibling()) {
            if (!(n instanceof Element e) || !VEFA.equals(e.getNamespaceURI())) continue;
            String value = e.getTextContent().trim();
            switch (e.getLocalName()) {
                case "scope" -> scope.add(value);
                case "success" -> success.add(value);
                case "error", "warning", "fatal" -> {
                    int count = e.hasAttribute("number") ? Integer.parseInt(e.getAttribute("number")) : 1;
                    if (count < 0) throw new IllegalArgumentException("Negative expectation count");
                    expected.put(e.getLocalName() + ":" + value, count);
                }
                case "description" -> { }
                default -> throw new IllegalArgumentException("Unknown VEFA expectation: " + e.getLocalName());
            }
        }
    }

    private static Element child(Element parent, String namespace, String name) {
        List<Element> matches = children(parent, namespace, name);
        return matches.isEmpty() ? null : matches.get(0);
    }

    private static List<Element> children(Element parent, String namespace, String name) {
        List<Element> result = new ArrayList<>();
        for (Node n = parent.getFirstChild(); n != null; n = n.getNextSibling()) {
            if (n instanceof Element e && namespace.equals(e.getNamespaceURI()) && name.equals(e.getLocalName())) result.add(e);
        }
        return result;
    }

    private static String json(Object value) {
        if (value instanceof Map<?, ?> map) {
            List<String> pairs = new ArrayList<>();
            map.forEach((k, v) -> pairs.add(json(k.toString()) + ":" + json(v)));
            return "{" + String.join(",", pairs) + "}";
        }
        if (value instanceof Iterable<?> list) {
            List<String> items = new ArrayList<>();
            list.forEach(item -> items.add(json(item)));
            return "[" + String.join(",", items) + "]";
        }
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value == null) return "null";
        StringBuilder text = new StringBuilder("\"");
        for (char c : value.toString().toCharArray()) {
            switch (c) {
                case '\\' -> text.append("\\\\");
                case '"' -> text.append("\\\"");
                case '\n' -> text.append("\\n");
                case '\r' -> text.append("\\r");
                case '\t' -> text.append("\\t");
                default -> { if (c < 32) text.append(String.format("\\u%04x", (int)c)); else text.append(c); }
            }
        }
        return text.append('"').toString();
    }
}
