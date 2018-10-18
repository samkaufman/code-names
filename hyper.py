#!/usr/bin/env python3

from itertools import product

OPTS = {
    'L': ['j'],
    'WALKCNT': [20, 100, 150],
    'ITERS': [1, 5, 10],
    'WINDOW_SIZE': [5, 10, 20, 30],
    'LIMIT': [10000, 20000],
    'VEC_DIM': [300]
}


def main():
    keys_s = sorted(list(OPTS.keys()))
    values_s = [OPTS[x] for x in keys_s]
    for config_vals in product(*values_s):
        c = dict(zip(keys_s, config_vals))
        cmd = f"make out/models/walks/embs-i{c['ITERS']}-w{c['WINDOW_SIZE']}-l{c['LIMIT']}-v{c['VEC_DIM']}-t{c['WALKCNT']}-{c['L']}.gensim " + " ".join(f"{k}={c[k]}" for k in c)
        print(cmd)


if __name__ == '__main__':
    main()
