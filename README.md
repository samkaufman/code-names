# code-names

This repository is a bundle of software artifacts for mining open source code
from GitHub and learning identifier embeddings from that code.

## How to Use

First, you can scrape GitHub for the **master** branches of all repositories
which show up while digging through the search results by language using the
script in `github-crawler` (e.g. `github-crawler/crawler.py -l java`). These
should end up in `out/corpora`.

After that, results can be produced by running `make`.

There are also some Jupyter notebooks under `notebooks`.

## What are these files?

- out/corpora/ - Repositories pulled from GitHub
- out/toks/trees/ - Tokenized code converted into S-expressions
- out/toks/preorder/ - Preorder traversals of those S-expressions
- out/subtoks/trees/ - Like `out/toks/trees`, but tokens are subtokenized
- out/subtoks/preorder/ - Preorder traversals of `out/subtoks/trees`
- out/subtoks/walks/ - Random AST walks of `out/subtoks/trees`
- out/models/ - Word embeddings vectors (Gensim format)
- out/evals/ - Text files describing tests on `models/`

## Hyperparameter Hints

Looking for performance? You probably want to use
`preorder/embs-i10-w20-l10000-v200-j.gensim` or

Remember that optimization is stochastic. You shouldn't expect wild swings in
performance, but you may not reproduce identical results at every run.

## Requirements

This code has been tested with Go 1.10.3, Java 1.8.0, and Python 3.6.5.