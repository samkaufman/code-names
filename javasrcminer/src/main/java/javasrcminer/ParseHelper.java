package javasrcminer;

import polyglot.ast.Lang;
import polyglot.ast.Node;
import polyglot.ext.jl7.JL7ExtensionInfo;
import polyglot.frontend.ExtensionInfo;
import polyglot.frontend.Parser;
import polyglot.frontend.Source;
import polyglot.main.Options;
import polyglot.util.ErrorQueue;
import polyglot.util.StdErrorQueue;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.InputStreamReader;

public class ParseHelper {
    private static ParseHelper ourInstance = new ParseHelper();

    public static ParseHelper getInstance() {
        return ourInstance;
    }

    private ParseHelper() {
    }
    
    public void parseAndVisit(File srcFile, NodeVisitorFactory visitorFactory) throws ParseException, FileNotFoundException {
        this.parseAndVisit(srcFile, false, visitorFactory);
    }
    
    public void parseAndVisit(File srcFile, Boolean disamb, NodeVisitorFactory visitorFactory) throws ParseException, FileNotFoundException {
        final Source fileSource = new DummyFileObject(srcFile.toURI());
        this.parseAndVisit(new FileReader(srcFile), fileSource, disamb, visitorFactory);
    }

    public void parseAndVisit(InputStreamReader reader, Source fileSource, Boolean disamb, NodeVisitorFactory visitorFactory) throws ParseException, FileNotFoundException {

        assert reader != null;
        assert fileSource != null;
        assert visitorFactory != null;
        
        // TODO: Do something with the ErrorQueue. Log?
        final ExtensionInfo extInfo = new JL7ExtensionInfo();
        final ErrorQueue eq = new StdErrorQueue(System.err, Integer.MAX_VALUE, extInfo.compilerName());
        Options.global = new Options(extInfo);

        // nf/tf are lazily constructed. Build them here to avoid nullptr excp. during parse()
        extInfo.nodeFactory();
        extInfo.typeSystem();
        final Lang lang = extInfo.nodeFactory().lang();
        assert lang != null;
        
        final Parser parser = extInfo.parser(reader, fileSource, eq);
        assert parser != null;

        // Parse the AST
        Node root;
        try {
            root = parser.parse();
        } catch (Exception e) {
            throw new ParseException("Exception raised during parse: " + e.toString(), e);
        }
        if (root == null) {
            throw new ParseException("parse returned null");
        }

        // If flag is set, disambiguate
        if (disamb) {
            // TODO: Implement
            assert root.isDisambiguated();
        }

        // Walk the AST
        try {
            root.visit(visitorFactory.makeVisitor(lang));
        } catch (Exception e) {
            throw new ParseException("Exception thrown during visit", e);
        } catch (StackOverflowError e) {
            // TODO: Catching a StackOverflowError? Ugh.
            throw new ParseException("Error during visit", e);
        }
    }

    public static class ParseException extends Exception {
        public ParseException(String msg) { super(msg); }
        public ParseException(String msg, Throwable cause) { super(msg, cause); }
    }
}
