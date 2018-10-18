#!/usr/bin/env python3

import argparse
from gensim.models.word2vec import Word2Vec
from sklearn.manifold import TSNE
from sklearn.externals import joblib


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action='store_true')
    parser.add_argument("--quick-test", action='store_true')
    parser.add_argument("tsne_path", metavar="TSNE")
    parser.add_argument("model_path", metavar="MODEL")
    args = parser.parse_args()

    model = Word2Vec.load(args.model_path)
    X = model[model.wv.vocab]  # c. norm
    if args.quick_test:
        X = X[:300]
    tsne = TSNE(verbose=(0 if args.quiet else 1))
    tsne.fit_transform(X)
    joblib.dump(tsne, args.tsne_path)


if __name__ == '__main__':
    main()
