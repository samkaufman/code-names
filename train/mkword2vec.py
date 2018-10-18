#!/usr/bin/env python3

import os
import sys
import re
import tarfile
import random
import logging
import argparse
from gensim.models import Word2Vec


FREQS_LINE_RE = re.compile(r'^\s*(\d+)\s+(.*)\s*$')


def load_freqs_from_vocab_file(fo):
    if isinstance(fo, str):
        with open(fo, 'r') as f:
            return load_freqs_from_vocab_file(f)

    freqs = {}
    for line in fo:
        if not line.strip():
            continue
        mo = FREQS_LINE_RE.match(line)
        freqs[mo.group(2)] = int(mo.group(1))
    return freqs


class ShuffleBuf:

    def __init__(self, distance=20000):
        self.distance = distance
        self.inner = []

    def push(self, item):
        self.inner.append(item)

    def pop(self):
        return self.inner.pop(random.randint(0, len(self.inner) - 1))

    def pop_all(self):
        random.shuffle(self.inner)
        to_r = self.inner
        self.inner = []
        return to_r

    def __len__(self):
        return len(self.inner)

    @property
    def is_full(self):
        return len(self.inner) >= self.distance


class AutodetectingCorpus:
    """Yields \"sentences\" from files, recursively, in given dirs/tarballs."""

    def __init__(self, srcs, shuffle=True):
        super().__init__()
        self._src_iters = []
        self._shuffle = shuffle
        for src in srcs:
            if isinstance(src, str) and os.path.isdir(src):
                tf = None
                members = [os.path.join(src, p) for p in os.listdir(src)]
            else:
                tf = src if isinstance(src, tarfile.TarFile) else tarfile.open(src, 'r')
                members = tf
            self._src_iters.append((tf, members))

    def __iter__(self):
        if not self._shuffle:
            yield from self._raw_iter()
        else:
            shuffle_buf = ShuffleBuf()
            for item in self._raw_iter():
                shuffle_buf.push(item)
                if shuffle_buf.is_full:
                    yield shuffle_buf.pop()
            yield from shuffle_buf.pop_all()

    def _raw_iter(self):
        for tf, members in self._src_iters:
            for member in members:
                body = None
                if isinstance(member, str):
                    # is a path
                    with open(member, 'r') as fo:
                        body = fo.read()
                elif member.isfile():
                    body = tf.extractfile(member).read().decode()
                if body:
                    body = body.strip()
                    for line in body.splitlines():
                        yield line.split()


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action='store_true')
    arg_parser.add_argument("--workers", type=int, default=4)
    arg_parser.add_argument("--iters", type=int, default=5)
    arg_parser.add_argument("--window_size", type=int, default=5)
    arg_parser.add_argument("--vec_dim", type=int, default=100)
    arg_parser.add_argument("--limit", type=int, default=10000)
    arg_parser.add_argument("--no-shuffle", action='store_true',
                            help="Don't shuffle training documents")
    arg_parser.add_argument("out_path", metavar="OUT",
                            help="Path to save model")
    arg_parser.add_argument("in_paths", metavar="TARFILE", nargs='+',
                            help="Path to tarballs to train over")
    args = arg_parser.parse_args()

    # Optionally be verbose
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)

    # Check for common problems saving to `out_path`. Painful UX to
    # finish training and *then* hit an exception
    out_path_dir = os.path.split(args.out_path)[0]
    if not os.path.isdir(out_path_dir):
        print(f"'{out_path_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # TODO: PYTHONHASHSEED, model `seed`, and `workers=1` for reproducibility
    corpus = AutodetectingCorpus(args.in_paths, shuffle=(not args.no_shuffle))
    model = Word2Vec(corpus,
                     sg=0,         # CBOW
                     cbow_mean=0,  # sums of context vectors (use `1` for mean)
                     size=args.vec_dim,     # vector dim.
                     window=args.window_size,
                     iter=args.iters,
                     workers=args.workers,
                     compute_loss=True,
                     max_vocab_size=args.limit)
    # TODO: `min_count = 1` once loading vocab.txt again
    # model.build_vocab_from_freq(load_freqs_from_vocab_file(sys.argv[1]))
    # model.train(TarfileCorpus(sys.argv[2]))
    model.save(args.out_path)


if __name__ == '__main__':
    main()
