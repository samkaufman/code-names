package javasrcminer;

import com.beust.jcommander.JCommander;
import com.beust.jcommander.MissingCommandException;
import com.beust.jcommander.Parameter;
import com.beust.jcommander.converters.PathConverter;
import org.apache.commons.lang3.StringEscapeUtils;

import javasrcminer.ParseHelper.ParseException;
import polyglot.ast.Id;
import polyglot.ast.LocalDecl;
import polyglot.ast.Node;
import polyglot.ast.NumLit;
import polyglot.ast.Prefix;
import polyglot.ast.Receiver;
import polyglot.ast.Return;
import polyglot.ast.StringLit;
import polyglot.ast.TypeNode;
import polyglot.ast.TypeNode_c;
import polyglot.ext.jl5.ast.AnnotationElem;
import polyglot.ext.jl5.ast.JL5AnnotatedElementExt;
import polyglot.visit.HaltingVisitor;
import polyglot.visit.NodeVisitor;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.stream.Stream;


final class Args {
}

@SuppressWarnings("CanBeFinal")
final class VocabArgs {
    @Parameter
    List<String> paths = new ArrayList<>();

    @Parameter(names = "--min-count", description = "Subtokens occurring fewer times are dropped")
    int minimumCount = 2;
}

@SuppressWarnings("CanBeFinal")
final class Dft2DocArgs {
    @Parameter
    List<String> paths = new ArrayList<>();

    @Parameter(names = "--vocab", description = "Write indices instead of tokens with given vocab file")
    String vocabPath = null;

    @Parameter(names = "--outdir", description = "Path to directory (nonexist.) for output documents", required = true, converter = PathConverter.class)
    Path outDirPath = null;
}

@SuppressWarnings("CanBeFinal")
final class Java2TreeArgs {
    @Parameter
    List<String> paths = new ArrayList<>();

    @Parameter(names = "--outdir", description = "Path to directory (nonexist.) for output documents", required = true, converter = PathConverter.class)
    Path outDirPath = null;

    @Parameter(names = "--include-syntax", description = "Include more than just subtokens and graph shape")
    Boolean includeSyntax = false;
}

@SuppressWarnings("CanBeFinal")
final class Token2SubtokenDocArgs {
    @Parameter(converter = PathConverter.class)
    List<Path> paths = new ArrayList<>();

    @Parameter(names = "--outdir", description = "Path to directory (nonexist.) for output documents", required = true, converter = PathConverter.class)
    Path outDirPath = null;
}

@SuppressWarnings("CanBeFinal")
final class TokTree2SubtokTreeArgs {
    @Parameter(converter = PathConverter.class)
    List<Path> paths = new ArrayList<>();

    @Parameter(names = "--outdir", description = "Path to directory (nonexist.) for output documents", required = true, converter = PathConverter.class)
    Path outDirPath = null;
}

/**
 * App
 * 
 * The primary entry point for the application.
 */
public final class App {
    public static void main(String[] argv) throws Exception {
        Args args = new Args();
        VocabArgs vocabArgs = new VocabArgs();
        Dft2DocArgs dft2DocArgs = new Dft2DocArgs();
        Java2TreeArgs java2TreeArgs = new Java2TreeArgs();
        Token2SubtokenDocArgs t2StDocArgs = new Token2SubtokenDocArgs();
        TokTree2SubtokTreeArgs tokTree2SubtokTreeArgs = new TokTree2SubtokTreeArgs();
        JCommander jc = new JCommander(args);
        jc.addCommand("vocab", vocabArgs);
        jc.addCommand("dft2doc", dft2DocArgs);
        jc.addCommand("java2tree", java2TreeArgs);
        jc.addCommand("t2st", t2StDocArgs);
        jc.addCommand("toktree2subtoktree", tokTree2SubtokTreeArgs);
        try {
            jc.parse(argv);
        } catch (MissingCommandException e) {
            System.err.println(e.getLocalizedMessage());
            System.exit(1);
            return;
        }

        // Switch to subcommand
        switch (jc.getParsedCommand()) {
            case "vocab": {
                makeVocabMain(vocabArgs);
                break;
            }
            case "dft2doc": {
                dft2DocMain(dft2DocArgs);
                break;
            }
            case "java2tree": {
                java2SexprTreeMain(java2TreeArgs);
                break;
            }
            case "t2st": {
                token2SubtokenDocMain(t2StDocArgs);
                break;
            }
            case "toktree2subtoktree": {
                tokTree2SubtokTreeMain(tokTree2SubtokTreeArgs);
                break;
            }
            default: {
                System.err.println("Unrecognized command: " + jc.getParsedCommand());
                System.exit(5);
            }
        }
    }

    // Map to S-expressions, either the full AST or simply shape+subtokens
    private static void java2SexprTreeMain(Java2TreeArgs args) throws Exception {
        
        // Create a VFS for the output directory/file and check/create output directory
        try (VFS outVFS = VFS.createVFSForPath(args.outDirPath)) {
            if (!outVFS.prepareOutputDirectory())
                return;

            final AtomicInteger filesParsed = new AtomicInteger(0);
            final AtomicInteger filesFailed = new AtomicInteger(0);
            final ParseHelper parseHelper = ParseHelper.getInstance();

            for (String topPath : args.paths) {
                try (VFS inVFS = VFS.createVFSForPath(Paths.get(topPath))) {
                    inVFS.forEachFile(".java", file -> {

                        assert file != null : "file was null";

                        try {
                            // Build in memory first for easier IOException control. Fast enough.
                            StringBuilder docBuilder = new StringBuilder();
                            final AtomicInteger openParens = new AtomicInteger(0);
                            parseHelper.parseAndVisit(file, lang -> new HaltingVisitor(lang) {

                                @Override
                                public NodeVisitor enter(Node parent, Node n) {
                                    assert openParens.addAndGet(1) >= 1;
                                    if (n instanceof Id) {
                                        final String idStr = ((Id)n).id();
                                        docBuilder.append(args.includeSyntax ? "(id [\"" : "[");
                                        List<String> subtokens = OldSubtokenizer.subtokenize(idStr);
                                        docBuilder.append(String.join((args.includeSyntax ? "\" \"" : " "), subtokens));
                                        docBuilder.append(args.includeSyntax ? "\"]" : "]");
                                        return bypassChildren(n);
                                    } else if (!args.includeSyntax) {
                                        docBuilder.append('(');
                                    } else if (n instanceof polyglot.ast.Assign) {
                                        docBuilder.append('(');
                                        docBuilder.append(((polyglot.ast.Assign) n).operator());
                                        docBuilder.append(' ');
                                    } else if (n instanceof polyglot.ast.Eval) {
                                        docBuilder.append("(e ");
                                    } else if (n instanceof polyglot.ast.Call) {
                                        docBuilder.append("(call ");
                                    } else if (n instanceof TypeNode) {
                                        String typeName = ((TypeNode) n).name();
                                        docBuilder.append("(type ");
                                        if (typeName == null) {
                                            docBuilder.append("'unnamed");
                                        } else {
                                            List<String> subtokens = OldSubtokenizer.subtokenize(typeName);
                                            docBuilder.append('[');
                                            docBuilder.append(String.join(" ", subtokens));
                                            docBuilder.append(']');
                                        }
                                        // docBuilder.append(")");
                                        return bypassChildren(n);
                                    } else if (n instanceof Prefix) {
                                        docBuilder.append("(prefix ");
                                    } else if (n instanceof polyglot.ast.While) {
                                        docBuilder.append("(while ");
                                    } else if (n instanceof polyglot.ast.New) {
                                        docBuilder.append("(new ");
                                    } else if (n instanceof LocalDecl) {
                                        docBuilder.append("(decl ");
                                    } else if (n instanceof Return) {
                                        docBuilder.append("(return ");
                                    } else if (n instanceof AnnotationElem) {
                                        docBuilder.append("(anno ");
                                    } else if (n instanceof Receiver) {
                                        docBuilder.append("(. ");
                                    } else if (n instanceof NumLit) {
                                        docBuilder.append(((NumLit) n).longValue());
                                    } else if (n instanceof StringLit) {
                                        docBuilder.append('"');
                                        // Should be a similar enough escape to avoid introducing
                                        // any systematic or frequent problems into the dataset.
                                        docBuilder.append(StringEscapeUtils.escapeJava(((StringLit) n).value()));
                                        docBuilder.append('"');
                                    } else {
                                        final String DROP_PREFIX = "polyglot.ast.";
                                        String fallbackName = n.getClass().getName();
                                        if (fallbackName.startsWith(DROP_PREFIX))
                                            fallbackName = fallbackName.substring(DROP_PREFIX.length());
                                        docBuilder.append('(');
                                        docBuilder.append(fallbackName);
                                        docBuilder.append(' ');
                                    }
                                    return this;
                                }

                                @Override
                                public Node leave(Node old, Node n, NodeVisitor v) {
                                    assert !(n instanceof Id);
                                    assert openParens.addAndGet(-1) >= 0;
                                    docBuilder.append(')');
                                    return n;
                                }
                            });

                            if (docBuilder.length() > 0) {
                                docBuilder.insert(0, "; " + file.getCanonicalPath() + "\n");
                                final String outFileName = String.format("%08d.txt", filesParsed.get());
                                outVFS.writeFile(outFileName, docBuilder.toString().getBytes());
                                // System.out.println(docBuilder.toString());
                                // System.out.println("");
                            }
                        } catch (Exception e) {
                            filesFailed.getAndIncrement();
                            String excDesc = e.toString();
                            if (e instanceof ParseException) {
                                Throwable cause = ((ParseException) e).getCause();
                                if (cause != null) {
                                    excDesc = cause.toString();
                                }
                            }
                            System.err.printf("Caught [%s]; skipping %s\n%s\n", excDesc, file.getPath(), e.getLocalizedMessage());
                        }

                        filesParsed.getAndIncrement();
                    });
                }
            }
        }
    }

    private static void tokTree2SubtokTreeMain(TokTree2SubtokTreeArgs args) throws Exception {
        
        try (VFS filesystemVFS = VFS.createVFSForPath(args.outDirPath)) {
            if (!filesystemVFS.prepareOutputDirectory())
                return;

            // Gather file paths
            Stream<Path> allPaths = args.paths.stream()
                    .flatMap(path -> {
                        try {
                            return Files.walk(path);
                        } catch (IOException e) {
                            System.err.println(e.toString());
                            System.exit(3);
                            return Stream.empty();
                        }
                    })
                    .filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().toLowerCase().endsWith(".txt"));

            // Start converting
            final Pattern pattern = Pattern.compile("([\\(\\)\\]\\s]*)([^\\(\\)\\[\\]\\s]*)", Pattern.CASE_INSENSITIVE);
            allPaths.forEach(inPath -> {
                try {
                    StringBuilder writer = new StringBuilder();
                    String inContents = new String(Files.readAllBytes(inPath), "UTF-8");
                    Matcher m = pattern.matcher(inContents);
                    while (m.find()) {
                        writer.append(m.group(1));
                        if (m.group(2).length() > 0)
                            writer.append("[" + String.join(" ", OldSubtokenizer.subtokenize(m.group(2))) + "]");
                    }
                    filesystemVFS.writeFile(inPath.getFileName().toString(), writer.toString().getBytes());
                } catch (IOException e) {
                    System.err.println(e.toString());
                    System.exit(4);
                }
            });
        }
    }

    // Pre-order DFT
    private static void dft2DocMain(Dft2DocArgs args) throws IOException, VocabFile.InvalidVocabFileException, IOException {
       
        // Create a VFS for the output directory/file
        FilesystemVFS outVFS = new FilesystemVFS(args.outDirPath);

        // Check/create output directory
        if (!outVFS.prepareOutputDirectory()) {
            outVFS.close();
            return;
        }

        int filesParsed = 0;
        int filesFailed = 0;
        final ParseHelper parseHelper = ParseHelper.getInstance();

        for (String topPath : args.paths) {
            // TODO: Make recursion a CLI arg

            final FilesystemVFS inVFS = new FilesystemVFS(Paths.get(topPath));
            final List<File> files = inVFS.crawlJavaPathsFromDirectory(Paths.get(topPath), ".java");

            for (File file : files) {
                assert file != null : "file was null";

                try {
                    // Build in memory first for easier IOException control. Fast enough.
                    StringBuilder docBuilder = new StringBuilder();
                    parseHelper.parseAndVisit(file, lang -> new NodeVisitor(lang) {
                        @Override
                        public NodeVisitor enter(Node parent, Node n) {
                            if (n instanceof Id) {
                                final String idStr = ((Id)n).id();
                                for (String subtoken : OldSubtokenizer.subtokenize(idStr))
                                    docBuilder.append(subtoken + " ");
                            }
                            return super.enter(n);
                        }
                    });

                    if (docBuilder.length() > 0) {
                        final String outFileName = String.format("%08d.txt", filesParsed);
                        Files.write(args.outDirPath.resolve(outFileName),
                                docBuilder.toString().getBytes());
                    }
                } catch (Exception e) {
                    filesFailed++;
                    System.err.printf("Caught exception; skipping %s\n%s\n", file.getPath(), e.getLocalizedMessage());
                }

                filesParsed++;
            }

            inVFS.close();
        }

        outVFS.close();
    }

    private static void makeVocabMain(VocabArgs args) throws IOException {

        // Fail fast on filesystem problems
        final String outFileName = "vocab.txt";
        PrintWriter vocabWriter = new PrintWriter(outFileName, "utf-8");  // TODO: Make name a CLI arg

        int filesParsed = 0;
        int filesFailed = 0;
        Map<String, Integer> counts = new HashMap<>(5000);
        ParseHelper parseHelper = ParseHelper.getInstance();

        final NodeVisitorFactory visitorFactory = lang -> new NodeVisitor(lang) {
            @Override
            public NodeVisitor enter(Node parent, Node n) {
                if (n instanceof Id) {
                    final String idStr = ((Id)n).id();
                    for (String subtoken : OldSubtokenizer.subtokenize(idStr)) {
                        counts.put(subtoken, 1 + counts.getOrDefault(subtoken, 0));
                    }
                }
                return super.enter(n);
            }
        };

        for (String topPath : args.paths) {
            List<File> files = (new FilesystemVFS(Paths.get(topPath))).crawlJavaPathsFromDirectory(Paths.get(topPath), ".java");

            for (File file : files) {
                assert file != null : "file was null";
                filesParsed++;
                try {
                    parseHelper.parseAndVisit(file, visitorFactory);
                } catch (Exception e) {
                    filesFailed++;
                    System.err.printf("Caught exception; skipping %s\n%s\n", file.getPath(), e.getLocalizedMessage());
                }
            }
        }

        // Sort in descending occurrence and print/write all 2+ occurs
        System.err.flush();
        List<String> tokens = new ArrayList<>(counts.keySet());
        tokens.sort((o1, o2) -> counts.get(o2) - counts.get(o1));
        for (String token : tokens) {
            if (counts.get(token) < args.minimumCount)
                break;
            System.out.printf("%d\t%s\n", counts.get(token), token);
            vocabWriter.printf("%d\t%s\n", counts.get(token), token);
        }
        System.out.printf("FILES FAILED: %d (of %d)\n", filesFailed, filesParsed);
        vocabWriter.close();
        System.out.println("Wrote to " + outFileName);
    }

    private static void token2SubtokenDocMain(Token2SubtokenDocArgs args) throws IOException {

        // Check/create output directory
        FilesystemVFS outVFS = new FilesystemVFS(args.outDirPath);
        if (!outVFS.prepareOutputDirectory())
            return;
        assert Files.isDirectory(args.outDirPath);

        // Gather file paths
        Stream<Path> allPaths = args.paths.stream()
            .flatMap(path -> {
                try {
                    return Files.walk(path);
                } catch (IOException e) {
                    System.err.println(e.toString());
                    System.exit(3);
                    return Stream.empty();
                }
            })
            .filter(Files::isRegularFile)
            .filter(path -> path.getFileName().toString().toLowerCase().endsWith(".txt"));

        // Start converting
        allPaths.forEach(inPath -> {
            Path outPath = args.outDirPath.resolve(inPath.getFileName());
            try {
                PrintWriter writer = new PrintWriter(Files.newBufferedWriter(outPath, StandardOpenOption.CREATE_NEW));
                try (Stream<String> lines = Files.lines(inPath)) {
                    lines
                        .map(line -> line.split("\\s+"))
                        .filter(toks -> toks.length > 0 && !toks[0].isEmpty())
                        .map(tokens -> {
                            StringBuilder b = new StringBuilder(2056);
                            int i = 0;
                            for (String token : tokens) {
                                for (String subtoken : OldSubtokenizer.subtokenize(token)) {
                                    if (i > 0)
                                        b.append(' ');
                                    b.append(subtoken);
                                    i++;
                                }
                            }
                            return b.toString();
                        })
                        .forEachOrdered(writer::println);
                    writer.close();
                }
            } catch (IOException e) {
                System.err.println(e.toString());
                System.exit(4);
            }
        });

        outVFS.close();
    }
}