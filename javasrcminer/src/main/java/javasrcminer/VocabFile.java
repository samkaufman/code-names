package javasrcminer;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class VocabFile {
    protected static Pattern linePattern = Pattern.compile("^\\s*(?<cnt>\\d+)\\s+(?<word>[^\\s]*)\\s*$");

    protected List<String> sortedWords = new ArrayList<>(2000);
    protected Map<String, Integer> word2idx = new HashMap<>();

    public VocabFile(Reader reader) throws InvalidVocabFileException, IOException {
        int lastSeenCount = Integer.MAX_VALUE;
        BufferedReader bufferedReader = new BufferedReader(reader);
        while (true) {
            final String line = bufferedReader.readLine();
            if (line == null)
                break;
            final String trimmedLine = line.trim();
            if (trimmedLine.length() == 0 || trimmedLine.startsWith("#") || trimmedLine.startsWith("//"))
                continue;
            final Matcher matcher = linePattern.matcher(trimmedLine);
            if (!matcher.matches())
                throw new InvalidVocabFileException("Couldn't parse line: " + trimmedLine);

            final int cnt = Integer.parseInt(matcher.group("cnt"));
            final String word = matcher.group("word");
            if (cnt > lastSeenCount)
                throw new InvalidVocabFileException("Improperly sorted vocab file");
            lastSeenCount = cnt;
            word2idx.put(word, sortedWords.size());
            sortedWords.add(word);
        }
    }

    public int getWordIndex(String word) {
        return word2idx.get(word);
    }

    public String getWord(int index) {
        return sortedWords.get(index);
    }

    public class InvalidVocabFileException extends Exception {
        public InvalidVocabFileException(String msg) {
            super(msg);
        }
    }
}
