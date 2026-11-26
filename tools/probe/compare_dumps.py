#!/usr/bin/env python3
"""Compare the engine-side dump (dump.cs -> engine-*.txt) with tfc_stats.py dump (resolved-*.txt).
Usage: python compare_dumps.py DIR   (DIR holds all four files). Top-level definition order differs
by design (the engine reorders through a Dictionary), so blocks are compared by name; the order of
children inside each definition must match exactly."""
import sys, os


def blocks(path):
    d, cur = {}, None
    for ln in open(path, newline="", encoding="utf-8").read().replace("\r\n", "\n").split("\n"):
        if ln.startswith("@@ "):
            cur = ln[3:]
            d[cur] = []
        elif cur is not None:
            d[cur].append(ln)
    return d


bad = 0
for kind in ("actors", "weapons"):
    e = blocks(os.path.join(sys.argv[1], "engine-%s.txt" % kind))
    r = blocks(os.path.join(sys.argv[1], "resolved-%s.txt" % kind))
    diff = [k for k in set(e) | set(r) if e.get(k) != r.get(k)]
    print("%s: engine %d, tfc_stats %d, differing definitions: %d" % (kind, len(e), len(r), len(diff)))
    bad += len(diff)
sys.exit(1 if bad else 0)
