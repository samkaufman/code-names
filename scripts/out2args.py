#!/usr/bin/env python3

import re
import os
import sys


CHARS_TO_LANGS = {
    'g': 'go',
    'p': 'python',
    'j': 'java'
}

NAME_RE = re.compile(r"embs-i(?P<iters>\d+)-w(?P<window>\d+)-l(?P<limit>\d+)-v(?P<vecdim>\d+)(-t(?P<walkcnt>\d+))?-(?P<langs>[" + ''.join(CHARS_TO_LANGS) + r"]+)\.gensim")

def main():
    dirpath, filename = os.path.split(sys.argv[1])
    walk_style = os.path.split(dirpath)[1]
    name_m = NAME_RE.match(filename)
    assert name_m is not None
    # langs = (CHARS_TO_LANGS[l] for l in name_m.group('langs'))
    langs = list(name_m.group('langs'))
    walkcnt_part = ""
    if name_m.group("walkcnt"):
        walkcnt_part = "-t" + name_m.group("walkcnt")
    if walk_style == 'walks':
        out_args = ' '.join(f"out/subtoks/{walk_style}/subtoks-walks{walkcnt_part}-{l}.tar.gz" for l in langs)
    elif walk_style == 'preorder':
        out_args = ' '.join(f"out/subtoks/{walk_style}/{CHARS_TO_LANGS[l]}" for l in langs)
    else:
        raise ValueError(f"Unexpected walk_style: {walk_style}")
    print(out_args)


if __name__ == '__main__':
    main()
