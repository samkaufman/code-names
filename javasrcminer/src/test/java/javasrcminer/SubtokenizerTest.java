package javasrcminer;

import static org.junit.Assert.assertArrayEquals;
import org.junit.Test;

public class SubtokenizerTest {
    @Test
    public void testOneSubtoken() {
        checkSubtok("add", new String[] { "add" });
    }

    @Test
    public void testMultipleUnderscores() {
        checkSubtok("a__beta", new String[] { "a", "beta" });
        checkSubtok("a___beta", new String[] { "a", "beta" });
        checkSubtok("a____beta", new String[] { "a", "beta" });
    }

    @Test
    public void testBasicSubtokenizations() {
        checkSubtok("setKind", new String[] {"set", "kind"});
        checkSubtok("COMPILE_GEN", new String[] {"compile", "gen"});
        checkSubtok("CAT123", new String[] {"cat", "123"});
        checkSubtok("CAT_123", new String[] {"cat", "123"});
        checkSubtok("Dog2Cat", new String[] { "dog", "2", "cat" });
        checkSubtok("2name", new String[] { "2", "name" });
        checkSubtok("2Name", new String[] { "2", "name" });
    }

    @Test
    public void testCapitalizedPrefixes() {
        checkSubtok("ASTParser", new String[] { "ast", "parser" });
        checkSubtok("AST2Parsed", new String[] { "ast", "2", "parsed" });
    }

    @Test
    public void testUnderscorePrefixes() {
        checkSubtok("_inner", new String[] { "_", "inner" });
    }

    @Test
    public void testUnderscoreAndCapitalizedPrefixes() {
        checkSubtok("_ASTParse", new String[] { "_", "ast", "parse" });
    }

    @Test
    public void testColonSourceString() {
        checkSubtok(":source:", new String[] { ":", "source", ":" });
        checkSubtok("::source::", new String[] { "::", "source", "::" });
    }

    @Test
    public void testAsterisk() {
        checkSubtok("*", new String[] { "*" });
    }

    @Test
    public void testQuotationMark() {
        checkSubtok("\"", new String[] { "\"" });
        checkSubtok("\"\"", new String[] { "\"\"" });
    }

    @Test
    public void testToTypeString() {
        checkSubtok(">type", new String[] { ">", "type" });
    }

    @Test
    public void testSlashes() {
        checkSubtok("hi/go", new String[] { "hi", "/", "go" });
        checkSubtok("/a/b", new String[] { "/", "a", "/", "b" });
    }

    @Test
    public void testDashes() {
        checkSubtok("-a-b-", new String[] { "-", "a", "-", "b", "-" });
    }

    @Test
    public void testTilde() {
        checkSubtok("~", new String[] { "~" });
    }

    @Test
    public void testClassSelector() {
        checkSubtok(".addthis-recommendedbox",
            new String[] { ".", "addthis", "-", "recommendedbox"});
    }

    @Test
    public void testEmoji() {
        checkSubtok("😄", new String[] { "😄" });
    }

    protected void checkSubtok(String token, String[] subtokens) {
        assertArrayEquals(subtokens, Subtokenizer.subtokenize(token).toArray());
    }
}
