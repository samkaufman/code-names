def doc_to_pairs(vocab, window_size: int, contents: str):
    for line in contents.splitlines():
        subtok_ids = [vocab.get(s, -1) for s in line.split()]  # -1 for unknown
        for pos, y in enumerate(subtok_ids):
            if y == -1:
                continue
            start = max(0, pos - window_size)
            window = enumerate(subtok_ids[start:(pos + window_size + 1)], start)
            yield from ((x, y) for i, x in window if i != pos and x != -1)
