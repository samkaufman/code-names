#!/usr/bin/env python3

import argparse
import ast
import multiprocessing as mp
import os
import warnings
from itertools import chain

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-t", "--trees", action='store_true')
arg_parser.add_argument("-r", "--recursive", action='store_true')
arg_parser.add_argument("-o", "--out", metavar="OUT", required=True)
arg_parser.add_argument("in_paths", metavar="IN", nargs='+')
args = arg_parser.parse_args()

# Check that `out` exists and is empty
if not os.path.isdir(args.out):
    raise ValueError(f"'{args.out}' is not a directory")
if len(os.listdir(args.out)):
    raise ValueError(f"'{args.out}' is not empty")

# Gather .py files
def yield_py_files(path):
    if not os.path.exists(path):
        raise ValueError(f"'{path}' doesn't exist")
    elif os.path.isfile(path):
        if os.path.splitext(path)[1].lower() == '.py':
            yield path
    elif args.recursive:
        for dirpath, _, filenames in os.walk(path):
            for n in filenames:
                yield from yield_py_files(os.path.join(dirpath, n))
    else:
        raise ValueError(f"'{path}' is a directory'")


def identifiers_from_node(node):
    # Yank every string not immediately in a `Str` node (only ids/names remain)
    if not isinstance(node, ast.Str):
        yield from (v for _, v in ast.iter_fields(node) if isinstance(v, str))


class NameChecker(ast.NodeVisitor):
    def visit(self, node):
        prefix = "  [ ] "
        if len(list(identifiers_from_node(node))):
            prefix = "  [*] "
        for fieldname, fieldval in ast.iter_fields(node):
            if isinstance(fieldval, str):
                part_a = prefix + node.__class__.__name__
                shift_a = " " * max(0, 30 - len(part_a))
                shift_b = " " * max(0, 60 - (len(part_a) + len(shift_a) + len(fieldname)))
                print(f"{part_a}{shift_a}{fieldname}{shift_b}{fieldval}")
        self.generic_visit(node)


class DFTWriter(ast.NodeVisitor):
    def __init__(self, out_file):
        super().__init__()
        self.out_file = out_file
        self.first = True

    def visit(self, node):
        for ident in identifiers_from_node(node):
            if not self.first:
                self.out_file.write(" ")
            self.first = False
            self.out_file.write(ident)
        self.generic_visit(node)
    

class TreeWriter(ast.NodeVisitor):
    def __init__(self, out_file):
        super().__init__()
        self.out_file = out_file

    def visit(self, node):
        self.out_file.write("(")
        for ident in identifiers_from_node(node):
            self.out_file.write(ident + " ")
        self.generic_visit(node)
        self.out_file.write(")")


def do_job(j):
    # TODO: Need to also handle Python 2
    try:
        seq_n, py_path = j
        filename = os.path.split(py_path)[1]
        parsed = ast.parse(open(py_path, 'r').read(), filename=filename)
        out_path = os.path.join(args.out, f"{seq_n:08d}.txt")
        with open(out_path, 'w') as f:
            if args.trees:
                visitor = TreeWriter(f)
            else:
                visitor = DFTWriter(f)
            visitor.visit(parsed)
    except Exception:
        warnings.warn("Exception while parsing Python; probably some Python 2")


with mp.Pool() as pool:
    jobs = enumerate(chain(*map(yield_py_files, args.in_paths)))
    for _ in pool.imap_unordered(do_job, jobs, 100):
        pass
