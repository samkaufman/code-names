package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/subcommands"
)

type dftCmd struct {
	includeLiterals bool
	outPath         string
}

func (*dftCmd) Name() string     { return "dft" }
func (*dftCmd) Synopsis() string { return "Dump preorder DFS traversal." }
func (*dftCmd) Usage() string {
	return `dft [-literals=false] -out <outdir> <inpaths>
	Dump preorder DFS traversal.	
`
}

func (d *dftCmd) SetFlags(f *flag.FlagSet) {
	f.StringVar(&d.outPath, "out", "", "An empty or non-existant to write token documents")
	f.BoolVar(&d.includeLiterals, "literals", true, "Include literals")
}

func (d *dftCmd) Execute(_ context.Context, f *flag.FlagSet, _ ...interface{}) subcommands.ExitStatus {

	inPaths := f.Args()
	if d.outPath == "" {
		fmt.Fprintf(os.Stderr, "-out required\n")
		return subcommands.ExitFailure
	}
	if len(inPaths) != 1 {
		fmt.Fprintf(os.Stderr, "exactly one path required\n")
		return subcommands.ExitFailure
	}

	helperErr := mainHelper(inPaths[0], d.outPath, func(f *ast.File, outW *bufio.Writer) {
		// Inspect the AST and print all identifiers and literals.
		wordsWritten := 0
		ast.Inspect(f, func(n ast.Node) bool {
			var s string
			switch x := n.(type) {
			case *ast.BasicLit:
				if d.includeLiterals {
					s = x.Value
				}
			case *ast.Ident:
				s = x.Name
			}

			if s != "" {
				if wordsWritten > 0 {
					if _, err := outW.WriteRune(' '); err != nil {
						panic(err)
					}
				}
				if _, err := outW.WriteString(s); err != nil {
					panic(err)
				}
				wordsWritten += 1
			}

			return true
		})
	})

	if helperErr != nil {
		fmt.Fprintf(os.Stderr, "error: %s\n", helperErr.Error())
		return subcommands.ExitFailure
	}
	return subcommands.ExitSuccess
}

type treesCmd struct {
	includeLiterals bool
	outPath         string
}

func (*treesCmd) Name() string     { return "trees" }
func (*treesCmd) Synopsis() string { return "Dump token trees." }
func (*treesCmd) Usage() string {
	return `trees [-literals=false] <outdir> <inpaths>
	Dump token trees.
`
}

func (t *treesCmd) SetFlags(f *flag.FlagSet) {
	f.StringVar(&t.outPath, "out", "", "An empty or non-existant to write token documents")
	f.BoolVar(&t.includeLiterals, "literals", true, "Include literals")
}

func (t *treesCmd) Execute(_ context.Context, f *flag.FlagSet, _ ...interface{}) subcommands.ExitStatus {

	inPaths := f.Args()
	if t.outPath == "" {
		fmt.Fprintf(os.Stderr, "-out required\n")
		return subcommands.ExitFailure
	}
	if len(inPaths) != 1 {
		fmt.Fprintf(os.Stderr, "exactly one path required\n")
		return subcommands.ExitFailure
	}

	helperErr := mainHelper(inPaths[0], t.outPath, func(f *ast.File, outW *bufio.Writer) {
		// Inspect the AST and print all identifiers and literals.
		ast.Inspect(f, func(n ast.Node) bool {
			if n == nil {
				if _, err := outW.WriteRune(')'); err != nil {
					panic(err)
				}
				return true
			}

			var s string
			switch x := n.(type) {
			case *ast.BasicLit:
				if t.includeLiterals {
					s = x.Value
				}
			case *ast.Ident:
				s = x.Name
			}

			if s != "" {
				if _, err := outW.WriteString(s); err != nil {
					panic(err)
				}
				if _, err := outW.WriteRune(' '); err != nil {
					panic(err)
				}
				return false // immediately jump up
			}

			if _, err := outW.WriteRune('('); err != nil {
				panic(err)
			}
			return true
		})
	})

	if helperErr != nil {
		fmt.Fprintf(os.Stderr, "error: %s\n", helperErr.Error())
		return subcommands.ExitFailure
	}
	return subcommands.ExitSuccess
}

func mainHelper(rootPath, outPath string, fileMapFunc func(*ast.File, *bufio.Writer)) error {

	rootSubs, err := ioutil.ReadDir(rootPath)
	if err != nil {
		return err
	}

	filesOpened := 0
	for _, subFileInfo := range rootSubs {
		projPath := filepath.Join(rootPath, subFileInfo.Name())

		fset := token.NewFileSet() // positions are relative to fse
		err := filepath.Walk(projPath, func(path string, info os.FileInfo, err error) error {
			filesOpened += 1
			if err != nil {
				return err
			}
			if info.IsDir() || strings.ToLower(filepath.Ext(projPath)) == ".go" {
				return nil
			}

			outFilePath := filepath.Join(outPath, fmt.Sprintf("%08d.txt", filesOpened))
			outF, err := os.OpenFile(outFilePath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
			if err != nil {
				return err
			}
			outW := bufio.NewWriter(outF)

			f, err := parser.ParseFile(fset, path, nil, 0)
			if err != nil {
				fmt.Fprintln(os.Stderr, "skipping: ", err)
				return nil
			}

			// Process
			fileMapFunc(f, outW)

			if err := outW.Flush(); err != nil {
				return fmt.Errorf("couldn't flush: %s", err.Error())
			}
			outF.Close()
			return nil
		})

		if err != nil {
			return err
		}
	}

	return nil
}

// This example demonstrates how to inspect the AST of a Go program.
func main() {
	subcommands.Register(subcommands.HelpCommand(), "")
	subcommands.Register(subcommands.FlagsCommand(), "")
	subcommands.Register(subcommands.CommandsCommand(), "")
	subcommands.Register(&dftCmd{}, "")
	subcommands.Register(&treesCmd{}, "")

	flag.Parse()
	ctx := context.Background()
	os.Exit(int(subcommands.Execute(ctx)))
}
