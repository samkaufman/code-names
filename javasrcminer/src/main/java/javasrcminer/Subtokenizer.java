package javasrcminer;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final public class Subtokenizer {
    private static Pattern leadingPattern = Pattern.compile("^(_+|[a-z]+)");
    private static Pattern bodyTokenPattern = Pattern.compile("" +
            "(_*)" +                                        // Cross (and discard) underscores
            "(?<subt>[A-Z]+(?=[^a-z]|$)" +
            "|\\.+|-+|:+|\\*+|\\&+|\\^+|[\"']+|[\\/]+|~+" + // Runs of some special characters
            "|[<>]+|[\\[\\]]+|[\\(\\)]+" +                  // Runs of same-parens
            "|\\d+" +                                       // Match any series of digits
            "|[A-Z]{2,}(?=[A-Z][a-z])" +
            "|[A-Z]?[a-z]+" +
            "|[A-Z]+$)");

    public static List<String> subtokenize(String token) {
        if (token.length() == 0) {
            throw new IllegalArgumentException("given zero-length token");
        }
        if (token.split("\\s").length != 1) {
            throw new IllegalArgumentException("given token had whitespace");
        }

        ArrayList<String> subtokens = new ArrayList<String>();

        Matcher leadingMatcher = leadingPattern.matcher(token);
        boolean consumedAll = false;
        int bodyStart = 0;
        if (leadingMatcher.lookingAt()) {
            bodyStart = leadingMatcher.end();
            subtokens.add(leadingMatcher.group().toLowerCase());
        }
        if (bodyStart == token.length())
            consumedAll = true;

        Matcher bodyMatcher = bodyTokenPattern.matcher(token);
        bodyMatcher.region(bodyStart, bodyMatcher.regionEnd());
        while (bodyMatcher.lookingAt()) {
            if (bodyMatcher.end() == token.length())
                consumedAll = true;
            subtokens.add(bodyMatcher.group("subt").toLowerCase());
            bodyMatcher.region(bodyMatcher.end(), bodyMatcher.regionEnd());
        }

        if (consumedAll) {
            return subtokens;
        }
        return Collections.singletonList(token);
    }
}
