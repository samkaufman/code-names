#!/usr/bin/env python3

import os
import sys
import re
import argparse
from queue import Queue
import threading
import traceback
from collections import defaultdict
import numpy as np
from typing import Optional, Mapping, Dict, Iterable
from tqdm import tqdm
import pyximport; pyximport.install()
from coocc_fast import doc_to_pairs
import pickle


def read_everything_in_dir(dirpath, include_cnt=False):
    """Yields the full contents of every file under `dirpath`.

    Even does it in a background thread. Lucky you!
    """
    if not os.path.isdir(dirpath):
        raise ValueError("not a directory: " + str(dirpath))
    all_filepaths = []
    for d, _, filepaths in os.walk(dirpath):
        all_filepaths += [os.path.join(d, p) for p in filepaths]

    should_stop, q = threading.Event(), Queue(maxsize=100)

    def bg_thread():
        try:
            for full_path in all_filepaths:
                try:
                    if should_stop.is_set():
                        return
                    with open(full_path, 'r') as fo:
                        contents = fo.read()
                    q.put(contents)
                except:
                    print(f"Exception while reading: {full_path}; skipping", file=sys.stderr)
                    traceback.print_exc()
        finally:
            q.put(None)

    t = threading.Thread(name="Reader-Thread", target=bg_thread, daemon=True)
    t.start()

    def contents_gen():
        try:
            while 1:
                msg = q.get()
                if msg is None:
                    break
                yield msg
        finally:
            should_stop.set()
            t.join(timeout=2)
            assert not t.is_alive()

    if include_cnt:
        return len(all_filepaths), contents_gen()
    return contents_gen()


def load_vocab(path: str, limit: Optional[int] = None) -> Mapping[str, int]:
    FREQS_LINE_RE = re.compile(r'^\s*(\d+)\s+(.*)\s*$')
    if not os.path.isfile(path):
        raise ValueError(f"'{path}' is not a file")
    with open(path, 'r') as fo:
        word2idx: Dict[str, int] = {}
        for line in fo:
            if not line.strip():
                continue
            mo = FREQS_LINE_RE.match(line)
            word2idx[mo.group(2)] = len(word2idx)
            if limit is not None and len(word2idx) == limit:
                break
        return word2idx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("window_size", metavar="WINDOW", type=int)
    parser.add_argument("vocab_path", metavar="VOCAB")
    parser.add_argument("data_path", metavar="SUBTOKS")
    parser.add_argument("out_path", metavar="OUT")
    args = parser.parse_args()

    if os.path.exists(args.out_path):
        print(f"{args.out_path} exists", file=sys.stderr)
        sys.exit(1)

    vocab = load_vocab(args.vocab_path, limit=args.limit)
    co_matrix = defaultdict(lambda: 0)
    cnt, reader = read_everything_in_dir(args.data_path, include_cnt=True)
    for contents in tqdm(reader, total=cnt):
        for x, y in doc_to_pairs(vocab, args.window_size, contents):
            a, b = sorted((x, y))
            co_matrix[(a, b)] += 1
    with open(args.out_path, 'wb') as out_fo:
        pickle.dump(dict(co_matrix), out_fo)


if __name__ == '__main__':
    main()
