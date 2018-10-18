#!/usr/bin/env python3

import re
import os
import pickle
import argparse
import gensim
import tabulate
import itertools
import numpy as np
from typing import Dict, List, Tuple
from pyfasttext import FastText


AnalogyDict = Dict[str, List[Tuple[str, str]]]


CONFIG_HEAD_RE = re.compile(r"^\[([\w\d\_\-\!]*)\]$")


class BaseReporter:

    def __init__(self, verbose=False, twodim=True):
        self.verbose = verbose
        self.twodim = twodim
        self._twodim_accum = []

    def report_analogy_check(self, a, b, c, expected, sims):
        if not self.verbose:
            return
        succeeded = (expected in [s[0] for s in sims])
        mainline_prefix = "[*]" if succeeded else "[ ]"
        self.write_text("%s checking %s : %s :: %s : [%s]" % (mainline_prefix, a, b, c, expected))
        self.write_text("     " + ', '.join(f"{s} {w:.2f}" for s, w in sims))

    def report_top_k(self, name, score, mean, sect_scores, skipped):
        self._twodim_accum.append((name, score, mean, sect_scores, skipped))
        if not self.twodim:
            self.write_vspace()
            self.flush()
            self._twodim_accum.clear()

    def flush(self):
        if not len(self._twodim_accum):
            return
        headers = [x[0] for x in self._twodim_accum]
        sect_names = list(self._twodim_accum[0][3].keys())
        table = [[n] + ["%.3f" % s[i] for s in self._twodim_accum]
                 for i, n in [(1, "OVERALL"), (2, "MEAN"), (4, "SKIPPED")]]
        table += [[n] + ["%.3f" % s[3][n] for s in self._twodim_accum]
                  for n in sect_names]
        self.write_table(table, headers=headers)


class StdoutReporter(BaseReporter):

    def write_header(self, header):
        print("")
        print(header)

    def write_text(self, text):
        print(text)

    def write_vspace(self):
        print("")

    def write_table(self, table, headers=None):
        print(tabulate.tabulate(table, headers=headers))


class HtmlReporter(BaseReporter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wrote_leader = False

    def _write_leader(self):
        if self._wrote_leader:
            return
        self._wrote_leader = True
        print("<html>")

    def write_header(self, header):
        self._write_leader()
        print("<h2>" + header + "</h2>")

    def write_text(self, text):
        self._write_leader()
        print(text + "<br />")

    def write_vspace(self):
        self._write_leader()
        print("<hr />")

    def write_table(self, table, headers=None):
        self._write_leader()
        print("<table>")
        # TODO: print header
        for row in table:
            print("<tr>")
            for item in row:
                print(f"<td>{str(item)}</td>")
            print("</tr>")
        print("</table>")


class FTWrapper:
    """Gives `pyfasttext.FastText` a `gensim`-like interface."""
    def __init__(self, ft):
        super().__init__()
        self.ft = ft
        self._words = None

    def most_similar(self, *args, **kwargs):
        new_kwargs = dict(kwargs)
        if 'topn' in new_kwargs:
            new_kwargs['k'] = new_kwargs['topn']
            del new_kwargs['topn']
        return self.ft.most_similar(*args, **new_kwargs)

    @property
    def index2word(self):
        if self._words is None:
            self._words = self.ft.words
        return self._words

    def __contains__(self, val):
        return val in self.index2word

    def __getitem__(self, x):
        return self.ft[x]


def read_analogies(fo) -> AnalogyDict:
    if isinstance(fo, str):
        with open(fo, 'r') as f:
            return read_analogies(f)

    sections: Dict[str, List[Tuple[str, str]]] = {}

    fo.seek(0)
    cur_section_title = None
    for line in fo:
        line = line.split('#')[0].strip()
        if len(line) == 0:
            continue
        config_match = CONFIG_HEAD_RE.match(line)
        if config_match:
            cur_section_title = config_match.group(1)
            sections[cur_section_title] = []
        else:
            a, b = line.split()
            sections[cur_section_title].append((a, b))

    return sections


def top_k_analogy_match(wv, k, analogies: AnalogyDict, reporter):
    # TODO: Delete `trials` and `sect_trials` state; fully det. by `analogies`
    trials = 0
    skipped = 0
    sect_trials = {sect_name: 0 for sect_name in analogies}
    sect_successes = {sect_name: 0 for sect_name in analogies}
    for section_name, sect in analogies.items():
        for (a, b), (c, d) in itertools.combinations(sect, 2):
            perms = [(a, b, c, d), (c, d, a, b), (b, a, d, c), (d, c, b, a)]
            for perm in perms:
                should_skip_perm = False
                if isinstance(wv, FastText):
                    if perm[-1] not in wv:
                        should_skip_perm = True
                        break
                else:
                    for x in perm:
                        if x not in wv:
                            should_skip_perm = True
                            break
                if should_skip_perm:
                    skipped += 1
                    break
                a_, b_, c_, expected = perm
                sims = wv.most_similar(positive=[b_, c_], negative=[a_], topn=k)
                reporter.report_analogy_check(a_, b_, c_, expected, sims)
                trials += 1
                sect_trials[section_name] += 1
                succeeded = (expected in [s[0] for s in sims])
                if succeeded:
                    sect_successes[section_name] += 1
    overall_success_rate = sum(sect_successes.values()) / trials
    sect_success_rate = {sname: (sect_successes[sname]/sect_trials[sname]) if sect_trials[sname] else 0.0
                         for sname in analogies}
    print(trials)
    mean_rate = sum(sect_success_rate.values()) / len(sect_success_rate)
    return overall_success_rate, mean_rate, sect_success_rate, skipped


def build_gensim_wv(words: List[str], embeddings: List[np.ndarray]):
    wv = gensim.models.keyedvectors.WordEmbeddingsKeyedVectors(embeddings[0].shape)
    wv.index2word = words
    wv.index2entity = words
    wv.vocab = {w: gensim.models.keyedvectors.Vocab(index=i)
                for i, w in enumerate(words)}
    wv.vectors = np.vstack(embeddings)
    return wv


def load_wv(path, filter_model_path=None, kind=['gensim', 'srcd', 'fasttext']):
    if isinstance(kind, str):
        return load_wv(path, [kind])

    # First, load the filtering model, if any. (FastText not supported atm.)
    to_try = kind[0]
    filter_wv = None
    if filter_model_path:
        filter_wv = load_wv(filter_model_path, kind=['gensim', 'srcd'])

    # Alright, now let's load the model, taking the filter into account.
    if to_try == 'gensim':
        try:
            if filter_wv and to_try != "fasttext":
                raise ValueError(f"`filter_model_path` not supported with {to_try}")
            return gensim.models.Word2Vec.load(path).wv
        except Exception:
            if len(kind) > 1:
                return load_wv(path, filter_model_path=filter_model_path, kind=kind[1:])
            raise
    elif to_try == 'srcd':
        try:
            if filter_wv and to_try != "fasttext":
                raise ValueError(f"`filter_model_path` not supported with {to_try}")
            with open(path, "rb") as fin:
                words, _, embeddings = pickle.load(fin)
            return build_gensim_wv(words, embeddings)
        except Exception:
            if len(kind) > 1:
                return load_wv(path, filter_model_path=filter_model_path, kind=kind[1:])
            raise
    elif to_try == 'fasttext':
        try:
            fasttext_wv = FTWrapper(FastText(path))
            if not filter_wv:
                return fasttext_wv
            words = filter_wv.index2word
            embeddings = [np.array(fasttext_wv[w]) for w in words]
            return build_gensim_wv(words, embeddings)
        except Exception:
            if len(kind) > 1:
                return load_wv(path, filter_model_path=filter_model_path, kind=kind[1:])
            raise
    else:
        raise ValueError(f"unknown kind {to_try}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("--html", action='store_true')
    parser.add_argument("--filter", "-f", metavar="MODEL", type=str)
    parser.add_argument("analogies_path", metavar="ANALOGIES")
    parser.add_argument("model_paths", metavar="MODELS", nargs='+')
    args = parser.parse_args()

    analogies = read_analogies(args.analogies_path)
    reporter_cls = HtmlReporter if args.html else StdoutReporter

    # Load either a gensim model or source{d}'s embeddings
    wvs = [load_wv(p, filter_model_path=args.filter) for p in args.model_paths]
    
    # If only one model is given, do a simple, detailed report:
    # report the summaries and, in verbose mode, the individual
    # analogy checks
    if len(wvs) == 1:
        reporter = reporter_cls(args.verbose, twodim=False)
        wv = wvs[0]
        for k in [1, 5, 20]:
            reporter.write_header(f"TOP-{k}")
            reporter.report_top_k("", *top_k_analogy_match(wv, k, analogies, reporter))
            reporter.flush()
    elif len(wvs) > 1:
        for k in [1, 5, 20]:
            reporter = reporter_cls(args.verbose)
            path_suffixes = [p[-24:] for p in args.model_paths]
            for p, wv in zip(path_suffixes, wvs):
                reporter.report_top_k(p, *top_k_analogy_match(wv, k, analogies, reporter))
            reporter.flush()
    else:
        raise Exception(f"unexpected wvs len: {len(wvs)}")


if __name__ == '__main__':
    main()
