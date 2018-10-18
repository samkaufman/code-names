package javasrcminer;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.List;
import java.util.function.Consumer;
import java.util.stream.Collectors;

public class FilesystemVFS implements VFS {

    private Path root = null;

    public FilesystemVFS(Path root) {
        assert root != null;
        this.root = root;
    }

    public void close() {}

    public boolean prepareOutputDirectory() throws IOException {
        boolean outExists = Files.exists(this.root);
        if (outExists) {
            if (Files.list(this.root).findAny().isPresent()) {
                System.err.printf("%s already exists and is non-empty", this.root.toAbsolutePath());
                System.exit(2);
                return false;
            }
        } else {
            Files.createDirectory(this.root);
        }
        return true;
    }

    public void unlinkDirectoryIfEmpty() throws IOException {
        if (!Files.isDirectory(this.root, LinkOption.NOFOLLOW_LINKS))
            return;
        if (Files.list(this.root).findAny().isPresent())
            return;
        Files.deleteIfExists(this.root);
    }
    public List<File> crawlJavaPathsFromDirectory(Path root, String ext) throws IOException {
        return Files.walk(root)
            .filter(Files::isRegularFile)
            .filter(path -> path.getFileName().toString().toLowerCase().endsWith(ext))
            .map(Path::toFile)
            .collect(Collectors.toList());
    }
    
    public void forEachFile(String ext, Consumer<File> it) throws IOException {
        List<File> files = this.crawlJavaPathsFromDirectory(this.root, ext);
        for (File file : files) {
            it.accept(file);
        }
    }
    
    public void writeFile(String path, byte[] bytes) throws IOException {
        Files.write(this.root.resolve(path), bytes);
    }
}