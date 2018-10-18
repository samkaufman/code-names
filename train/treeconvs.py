#!/usr/bin/env python3

import os
import sys
import math
import random
import tarfile
import argparse
import traceback
from io import BytesIO
from typing import Iterable, List, cast


class UnbalancedParens(Exception):
    pass


class Node:
    __slots__ = ['subtoks', 'parent', 'children']

    def __init__(self, parent):
        self.parent = parent
        self.children = []
        self.subtoks = []

    def nodes(self):
        """Returns self and all children, recursively."""
        yield self
        for s in self.children:
            yield from s.nodes()

    def sample_conv_path(self, size=None):
        assert size is None or size % 2 == 1
        sidelen = math.inf if size is None else int(size / 2)
        visited = set([self])
        left, right = [], []
        for side in (left, right):
            root = self
            while len(side) < sidelen:
                options = set([root.parent] + root.children) - visited
                options = set(x for x in options if x is not None)
                if len(options) == 0:
                    break
                root = random.choice(list(options))
                visited.add(root)
                side.append(root)
        left.reverse()
        return left + [self] + right

    def reachable_subtoks(self, max_distance, include_self=True) -> Iterable[str]:
        for n in self.reachable(max_distance, include_self=include_self):
            yield from n.subtoks

    def reachable(self, max_distance, include_self=True, visited=set()) -> Iterable['Node']:
        """Yield all Nodes reachable at `max_distance`.

        `visited` is a set of Nodes not to explore. Will be mutated!
        """
        visited.add(id(self))
        if include_self:
            yield self
        if max_distance:
            for n in [self.parent] + self.children:
                if n is None or id(n) in visited:
                    continue
                yield from n.reachable(max_distance - 1, visited=visited)

    def __str__(self):
        ss = ' '.join(self.subtoks)
        cc = ' '.join(str(c) for c in self.children)
        to_join = [x for x in (ss, cc) if x]
        return "(%s)" % (' '.join(to_join,))


def read_sfile(fo) -> Iterable[Node]:
    lines = [l.strip() for l in fo if not l.strip().startswith(';')]
    assert len(lines) == 1, f"Got {len(lines)} lines"
    return _parse_paren(lines[0])


def _parse_paren(expr) -> Iterable[Node]:
    stack: List[Node] = []
    pending_word = ''
    for ch in expr:
        if ch == ' ':
            if pending_word:
                stack[-1].subtoks.append(pending_word)
                pending_word = ''
        elif ch == '(':
            if len(stack):
                n = Node(stack[-1])
                stack[-1].children.append(n)
            else:
                n = Node(None)
            stack.append(cast(Node, n))
        elif ch == ')':
            if pending_word:
                stack[-1].subtoks.append(pending_word)
                pending_word = ''
            if len(stack) == 1:
                yield stack[-1]
            try:
                stack.pop()
            except IndexError:
                raise UnbalancedParens()
        elif ch in '[]':
            # We ignore […] subtoken parentheticals
            pass
        else:
            pending_word += ch


def _map_nodetree_to_graph(node, g, highlight=[], center=None):
    assert center in highlight
    kwargs = {'label': ' '.join(node.subtoks)}
    if id(node) in highlight:
        color = 'lightgrey' if id(node) == center else 'green'
        kwargs.update(style='filled', color=color)
    g.node(str(id(node)), **kwargs)
    if node.parent is not None:
        g.edge(str(id(node)), str(id(node.parent)))
    for child in node.children:
        _map_nodetree_to_graph(child, g, highlight=highlight, center=center)


class OutDirlike:
    def __init__(self, path):
        self.rootpath = path
        self.tf = None
        p_l = path.lower()
        if p_l.endswith('.tar') or p_l.endswith('.tar.gz'):
            mode = 'w'
            if path.lower().endswith('.tar.gz'):
                mode = 'w:gz'
            self.tf = tarfile.open(path, mode)
        else:
            os.makedirs(path, exist_ok=False)

    def addfile(self, filepath, body):
        if self.tf is None:
            full_out_path = os.path.join(self.rootpath, filepath)
            assert not os.path.exists(full_out_path)
            with open(full_out_path, 'wb') as fo:
                fo.write(body)
        else:
            ti = tarfile.TarInfo(name=filepath)
            ti.size = len(body)
            self.tf.addfile(ti, BytesIO(body))

    def close(self):
        if self.tf is not None:
            self.tf.close()


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcmd')
    parser_graphtest = subparsers.add_parser('graphtest')
    parser_graphtest.add_argument('in_path', metavar='IN')
    parser_walks = subparsers.add_parser('walks')
    parser_walks.add_argument('--count', type=int, default=20)
    parser_walks.add_argument('in_path', metavar='IN')
    parser_walks.add_argument('out_path', metavar='OUT')
    args = parser.parse_args()

    # Kick the tires on the file given as first argument
    if args.subcmd == 'graphtest':
        with open(args.in_path, 'r') as fo:
            for n in read_sfile(fo):
                # print(n)
                # print("")
                # example_node = n.children[1].children[0].children[1].children[0]
                # for subtok in example_node.reachable_subtoks(4):
                #     print(subtok)
                example_node = n.children[1].children[0].children[1].children[0]
                reachables = set(map(id, example_node.sample_conv_path(4*2 + 1)))
                from graphviz import Graph
                g = Graph()
                _map_nodetree_to_graph(n, g, highlight=reachables, center=id(example_node))
                g.view()
    elif args.subcmd == 'walks':
        assert os.path.isdir(args.in_path)
        out_dirlike = OutDirlike(args.out_path)
        for d, _, filepaths in os.walk(args.in_path):
            for p in filepaths:
                ip = os.path.join(d, p)
                op = os.path.join(args.out_path, p)
                assert not os.path.exists(op)  # hacky; just prevent conflicts
                with open(ip, 'r') as io:
                    try:
                        for root in read_sfile(io):
                            nonempty = [n for n in root.nodes() if len(n.subtoks)]
                            if len(nonempty) == 0:
                                continue
                            for centroid in random.choices(nonempty, k=args.count):
                                path = centroid.sample_conv_path()
                                path_subtoks = [s for n in path for s in n.subtoks]
                                out_dirlike.addfile(p, (' '.join(path_subtoks) + '\n').encode())
                    except UnbalancedParens:
                        print(f"Unbalanced parens; skipping & leaving partial",
                              file=sys.stderr)
                    except Exception:
                        print(f"Exception on {ip}; skipping & leaving partial",
                              file=sys.stderr)
                        traceback.print_exc()
        out_dirlike.close()

if __name__ == '__main__':
    main()
