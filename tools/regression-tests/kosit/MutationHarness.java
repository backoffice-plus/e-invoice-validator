import de.kosit.xmlmutate.mutation.Mutation;
import de.kosit.xmlmutate.mutation.Schematron;
import de.kosit.xmlmutate.runner.FailureMode;
import de.kosit.xmlmutate.runner.MutationRunner;
import de.kosit.xmlmutate.runner.RunMode;
import de.kosit.xmlmutate.runner.RunnerConfig;
import de.kosit.xmlmutate.runner.SavingMode;
import de.kosit.xmlmutate.schematron.SchXsltSchematronCompiler;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;

/** Thin adapter around the exact XML-Mutate version used by the upstream releases. */
public final class MutationHarness {
    static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"")
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }

    public static void main(String[] args) throws Exception {
        org.apache.logging.log4j.core.config.Configurator.setRootLevel(org.apache.logging.log4j.Level.ERROR);
        if (args[0].equals("--compile-schematron")) {
            Path directory = Path.of(args[2]).toAbsolutePath();
            Files.createDirectories(directory);
            // XML-Mutate's compiler adapter returns the source document URI for .sch inputs.
            // The report test needs the generated DOM persisted as a real XSLT instead.
            var compiled = new name.dmaus.schxslt.Compiler().compile(
                new javax.xml.transform.stream.StreamSource(Path.of(args[1]).toFile()),
                java.util.Map.of());
            Path stylesheet = directory.resolve("report-validation.xsl");
            javax.xml.transform.TransformerFactory.newInstance().newTransformer().transform(
                new javax.xml.transform.dom.DOMSource(compiled),
                new javax.xml.transform.stream.StreamResult(stylesheet.toFile()));
            Files.writeString(directory.resolve("compiled-path.txt"), stylesheet.toString());
            return;
        }
        Path sourceRoot = Path.of(args[0]).toAbsolutePath();
        Path target = Path.of(args[1]).toAbsolutePath();
        Files.createDirectories(target);
        List<Path> documents = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(args[2]))) {
            if (!line.isBlank()) documents.add(Path.of(line).toAbsolutePath());
        }
        List<Schematron> schematrons = new ArrayList<>();
        for (int i = 3; i < args.length; i++) {
            String[] pair = args[i].split("=", 2);
            var compiler = new SchXsltSchematronCompiler();
            var uri = compiler.compile(target, Path.of(pair[1]).toAbsolutePath().toUri());
            // These are the deployed, precompiled XSLTs, never freshly rebuilt rule sources.
            if (!uri.equals(Path.of(pair[1]).toAbsolutePath().toUri())) {
                throw new IllegalStateException("Rule XSLT was unexpectedly recompiled: " + pair[1]);
            }
            schematrons.add(new Schematron(pair[0], uri, compiler.extractRuleIds()));
        }
        // Framework caches are shared. One worker also keeps mutation filenames deterministic.
        var executor = Executors.newSingleThreadExecutor();
        try (var writer = Files.newBufferedWriter(target.resolve("results.jsonl"), StandardCharsets.UTF_8)) {
            var config = RunnerConfig.Builder.forDocuments(documents)
                .mode(RunMode.ALL).targetFolder(target).withExecutor(executor)
                .withSavingMode(SavingMode.SINGLE).withFailureMode(FailureMode.FAIL_AT_END)
                .checkSchematron(schematrons).reportWith((results, mode) -> {}).build();
            var result = new MutationRunner(config, executor).run();
            for (var file : result.getResult()) {
                String source = sourceRoot.relativize(file.getLeft()).toString().replace('\\', '/');
                writer.write("{\"type\":\"source\",\"source\":" + quote(source)
                    + ",\"mutations\":" + file.getRight().size() + "}\n");
                for (Mutation mutation : file.getRight()) {
                    String key = source + "#" + mutation.getIdentifier();
                    var matches = mutation.getResult().getSchematronExpectationMatches();
                    var expectations = mutation.getConfiguration().getSchematronExpectations();
                    var container = mutation.getMutationErrorContainer();
                    var executionErrors = new ArrayList<String>();
                    boolean missingRule = false;
                    for (String error : container.getAllErrorMessages()) {
                        boolean expectationMessage = false;
                        for (var expectation : expectations) {
                            String failed = "Failed rule " + expectation.getRuleName();
                            if (error.equals(failed) || error.startsWith(failed + " instruction ")) {
                                expectationMessage = true;
                            }
                            if (error.equals("Rule " + expectation.getRuleName()
                                + " does not exist in schematron " + expectation.getSource())) {
                                missingRule = true;
                                expectationMessage = true;
                            }
                        }
                        // Pinned XML-Mutate exposes these two conditions only as rendered strings.
                        // Every other tool/parser/transform error is an unconditional test failure.
                        if (!expectationMessage) executionErrors.add(error);
                    }
                    if (matches.size() != expectations.size() || !executionErrors.isEmpty()) {
                        writer.write("{\"type\":\"error\",\"key\":" + quote(key)
                            + ",\"detail\":" + quote("state=" + mutation.getState()
                                + ", expected=" + expectations.size() + ", evaluated=" + matches.size()
                                + ", errors=" + executionErrors) + "}\n");
                    }
                    for (var expectation : expectations) {
                        String id = expectation.getSource() + ":" + expectation.getRuleName();
                        writer.write("{\"type\":\"expectation\",\"key\":" + quote(key + "#" + id
                                + "#" + expectation.getExpectedResult())
                            + ",\"source\":" + quote(source)
                            + ",\"mutation\":" + quote(mutation.getIdentifier())
                            + ",\"rule\":" + quote(id)
                            + ",\"expected\":" + quote(expectation.getExpectedResult().toString())
                            + ",\"missing_rule\":" + missingRule
                            + ",\"passed\":" + Boolean.TRUE.equals(matches.get(expectation)) + "}\n");
                    }
                }
            }
        } finally {
            executor.shutdownNow();
        }
    }
}
