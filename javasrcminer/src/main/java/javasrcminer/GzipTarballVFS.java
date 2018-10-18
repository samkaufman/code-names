package javasrcminer;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Consumer;

import org.apache.commons.compress.archivers.ArchiveEntry;
import org.apache.commons.compress.archivers.tar.TarArchiveEntry;
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream;
import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream;
import org.apache.commons.compress.compressors.gzip.GzipCompressorOutputStream;

public class GzipTarballVFS implements VFS {

    private Path path;
    private TarArchiveInputStream inputStream;
    private TarArchiveOutputStream outputStream;

    public GzipTarballVFS(Path tarballPath) {
        assert tarballPath.getFileName().toString().toLowerCase().endsWith(".tar.gz");
        this.path = tarballPath;
    }

    public void close() throws IOException {
        if (this.inputStream != null) {
            this.inputStream.close();
        }
        if (this.outputStream != null) {
            this.outputStream.close();
        }
    }

    public boolean prepareOutputDirectory() throws IOException {
        if (Files.exists(this.path)) {
            System.err.printf("%s already exists", this.path.toAbsolutePath());
            System.exit(2);
            return false;
        }
        return true;
    }

    public void unlinkDirectoryIfEmpty() throws IOException {
        if (Files.exists(this.path) && Files.size(this.path) == 0) {
            Files.deleteIfExists(this.path);
        }
    }

    public void forEachFile(String ext, Consumer<File> it) throws IOException {
        // TODO: Implement
        assert false;
    }

    public void writeFile(String path, byte[] bytes) throws IOException {
        openAsOutputFile();

        TarArchiveEntry entry = new TarArchiveEntry(path);
        entry.setSize(bytes.length);

        this.outputStream.putArchiveEntry(entry);
        this.outputStream.write(bytes);
        this.outputStream.closeArchiveEntry();
    }

    private void openAsOutputFile() throws IOException {
        if (this.outputStream != null) {
            return;
        }
        assert this.inputStream == null;

        FileOutputStream fileOut = new FileOutputStream(this.path.toString());
        BufferedOutputStream buffOut = new BufferedOutputStream(fileOut);
        GzipCompressorOutputStream gzOut = new GzipCompressorOutputStream(buffOut);
        this.outputStream = new TarArchiveOutputStream(gzOut);
    }
}