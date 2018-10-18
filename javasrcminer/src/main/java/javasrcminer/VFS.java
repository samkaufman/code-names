package javasrcminer;

import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.function.Consumer;

public interface VFS extends AutoCloseable {
    public static VFS createVFSForPath(Path path) throws IOException {
        if (path.getFileName().toString().toLowerCase().endsWith(".tar.gz")) {
            return new GzipTarballVFS(path);
        }
        return new FilesystemVFS(path);
    }

    void close() throws Exception;

    boolean prepareOutputDirectory() throws IOException;

    void unlinkDirectoryIfEmpty() throws IOException;
    
    void forEachFile(String ext, Consumer<File> it) throws IOException;
    
    void writeFile(String path, byte[] bytes) throws IOException;
}
