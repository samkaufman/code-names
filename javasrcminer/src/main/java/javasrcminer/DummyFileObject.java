package javasrcminer;

import com.ibm.wala.util.debug.UnimplementedError;
import polyglot.frontend.Source;

import javax.tools.JavaFileObject;
import javax.tools.SimpleJavaFileObject;
import java.net.URI;
import java.nio.file.Paths;

/**
 * DummyFileObject
 *
 * A simple implementation of SimpleJavaFileObject and Source which
 * returns the path and name of a provided File, as well as USER_SPECIFIED
 * and COMPILER_GENERATED.
 */
final class DummyFileObject extends SimpleJavaFileObject implements Source {

    private String path;
    private String fileName;

    public DummyFileObject(URI fileURI) {
        super(fileURI, JavaFileObject.Kind.SOURCE);
        assert uri.getScheme().equalsIgnoreCase("file");
        this.path = Paths.get(fileURI.getPath()).normalize().toString();
        this.fileName = Paths.get(this.path).getFileName().toString();
    }

    // public DummyFileObject(File file) {
    //     // super(file.toURI(), JavaFileObject.Kind.SOURCE);
    //     // assert uri.getScheme().equalsIgnoreCase("file");
    //     // this.path = file.getPath().toString();
    //     // this.fileName = file.getName();
    //     this(file.toURI());
    // }

    @Deprecated
    @Override
    public void setUserSpecified(boolean userSpecified) {
        throw new UnimplementedError();
    }

    @Override
    public boolean userSpecified() {
        return kind() == Source.Kind.USER_SPECIFIED;
    }

    @Override
    public boolean compilerGenerated() {
        return kind() == Source.Kind.COMPILER_GENERATED;
    }

    @Override
    public void setKind(Source.Kind kind) {
        throw new UnimplementedError();
    }

    @Override
    public Source.Kind kind() {
        return Source.Kind.USER_SPECIFIED;
    }

    @Override
    public String name() {
        return this.fileName;
    }

    @Override
    public String path() {
        return this.path;
    }
}
