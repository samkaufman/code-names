# Hyperparameters
WALKCNT=100
ITERS=5
WINDOW_SIZE=20
LIMIT=10000
VEC_DIM=300


.PHONY: all

LANGS = java python go
LC_PERMS = j p jp jg pg jpg
ALL_SUBTOKS = $(foreach lang,$(LANGS),out/subtoks/preorder/$(lang) out/subtoks/trees/$(lang))
ALL_EVALS = $(foreach c,$(LC_PERMS),out/evals/preorder-i$(ITERS)-w$(WINDOW_SIZE)-l$(LIMIT)-v$(VEC_DIM)-$(c)-eval.txt out/evals/walks-i$(ITERS)-w$(WINDOW_SIZE)-l$(LIMIT)-v$(VEC_DIM)-t$(WALKCNT)-$(c)-eval.txt)
all: $(ALL_SUBTOKS) $(ALL_EVALS)


#
# Per-language S-trees
#
# (We don't do `toks` for Java since it's mainly just to get our data
# into javasrcminer.)
#
out/toks/trees/python: | out/corpora/python
	mkdir -p $@ && \
	cd pythonsrcminer && \
	python3 -m pythonsrcminer -t -r -o ../$@ ../$|

out/toks/trees/go: | out/corpora/go
	mkdir -p $@ && \
	go run gosrcminer/src/gosrcminer/main.go trees -out $@ $|

out/subtoks/trees/%: | out/toks/trees/%  # TODO: use out/subtoks/trees/subtoks-trees-%.tar.gz
	mkdir -p out/subtoks/trees && \
	javasrcminer/gradlew --no-daemon run -p javasrcminer '-D=exec.args=toktree2subtoktree --outdir ../$@ ../$|'

out/subtoks/trees/java: | out/corpora/java  # TODO: use out/subtoks/trees/subtoks-trees-java.tar.gz
	mkdir -p out/subtoks/trees && \
	javasrcminer/gradlew --no-daemon run -p javasrcminer '-D=exec.args=java2tree --outdir ../$@ ../$|'


#
# Preorder walks for everything but Java.
#
# (Why aren't these constructed using from `out/trees`? History. Tech debt.)
#
out/toks/preorder/go: | out/corpora/go
	mkdir -p $@ && \
	go run gosrcminer/src/gosrcminer/main.go dft -out $@ $|

out/toks/preorder/python: | out/corpora/python
	mkdir -p $@ && \
	cd pythonsrcminer && \
	python3 -m pythonsrcminer -r -o ../$@ ../$|


# Convert those preorder traversals into subtokenized preorder traversals
out/subtoks/preorder/%: | out/toks/preorder/%
	mkdir -p $@ && javasrcminer/gradlew run -p javasrcminer '-D=exec.args=t2st --outdir $(addprefix ../,$@ $|)'

out/subtoks/preorder/java: | out/corpora/java
	mkdir -p $@ && javasrcminer/gradlew run -p javasrcminer '-D=exec.args=dft2doc --outdir $(addprefix ../,$@ $|)'

# Build some random walks
out/subtoks/walks/subtoks-walks-t$(WALKCNT)-%.tar.gz: | out/subtoks/trees/%
	mkdir -p out/subtoks/walks && python3 train/treeconvs.py walks --count $(WALKCNT) $| $@


#
# Embeddings
#

# TODO: These all depend on *all* subtoks, which is wrong
out/models/preorder/embs-i$(ITERS)-w$(WINDOW_SIZE)-l$(LIMIT)-v$(VEC_DIM)-%.gensim: | $(foreach l,$(LANGS),out/subtoks/preorder/$(l))
	mkdir -p out/models/preorder && \
	train/mkword2vec.py -v --iters $(ITERS) --window_size $(WINDOW_SIZE) --limit $(LIMIT) --vec_dim $(VEC_DIM) $@ `scripts/out2args.py $@`


# out/models/walks/embs-i$(ITERS)-w$(WINDOW_SIZE)-l$(LIMIT)-v$(VEC_DIM)-t$(WALKCNT)-%.gensim: | $(foreach l,$(LANGS),out/subtoks/walks/subtoks-walks-t$(WALKCNT)-$(l).tar.gz)

out/models/walks/embs-i$(ITERS)-w$(WINDOW_SIZE)-l$(LIMIT)-v$(VEC_DIM)-t$(WALKCNT)-%.gensim: $(foreach l,$(LANGS),out/subtoks/walks/subtoks-walks-t$(WALKCNT)-$(l).tar.gz)
	mkdir -p out/models/walks && \
	train/mkword2vec.py -v --iters $(ITERS) --window_size $(WINDOW_SIZE) --limit $(LIMIT) --vec_dim $(VEC_DIM) $@ `scripts/out2args.py $@`


#
# Analysis
#
# TODO: These all depend on *all* models, which is very, very wrong
#

out/evals/preorder-%-eval.txt: eval/eval.py eval/lists/analogies.txt out/models/preorder/embs-%.gensim
	mkdir -p out/evals && \
	eval/eval.py -v eval/lists/analogies.txt out/models/preorder/embs-$*.gensim > $@

out/evals/walks-%-eval.txt: eval/eval.py eval/lists/analogies.txt out/models/walks/embs-%.gensim
	mkdir -p out/evals && \
	eval/eval.py -v eval/lists/analogies.txt out/models/walks/embs-$*.gensim > $@
