package javasrcminer;

import polyglot.ast.Lang;
import polyglot.visit.NodeVisitor;

public interface NodeVisitorFactory {
    NodeVisitor makeVisitor(Lang lang);
}
