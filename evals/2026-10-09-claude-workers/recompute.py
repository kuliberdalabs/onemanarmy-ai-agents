#!/usr/bin/env python3
"""Recompute every number in README.md from ledger.csv and judge_scores.csv.

Usage: python3 recompute.py        (run from any directory; stdlib only)
Cells written `unknown` or `n/a` are skipped, never read as zero.
"""
import collections, csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
# USD per million tokens (input, output). Cache write 1.25x input, cache read 0.1x input.
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0),
         "claude-opus-5-5": (4.0, 20.0), "claude-fable-5-1": (10.0, 50.0)}
CLASSES = ["classify", "fix", "diagnose", "diagnose-open", "sweep", "generalize", "write-pl", "build"]


def group(r):
    if r["task"].endswith("fable-plan-for-haiku"):
        return "fable plan only"
    if r["task"].endswith("+fable-plan"):
        return "haiku + fable plan (worker rows)"
    return r["model_id"]


def proxy(r):
    p_in, p_out = PRICE[r["model_id"]]
    i, c, o = (int(r[k]) for k in ("input_tokens", "cached_input_tokens", "output_tokens"))
    return ((i - c) * p_in * 1.25 + c * p_in * 0.1 + o * p_out) / 1e6


rows = list(csv.DictReader(open(os.path.join(HERE, "ledger.csv"))))
by = collections.defaultdict(list)
for r in rows:
    by[group(r)].append(r)

print("== gates: group, rows, graded, accepted, grader >= 0.95")
for g, rs in by.items():
    graded = [r for r in rs if r["score"] not in ("n/a", "unknown")]
    if graded:
        print(f"{g}: rows={len(rs)} graded={len(graded)} accepted={sum(r['result'] == 'accepted' for r in graded)} "
              f"grader_pass={sum(float(r['score']) >= 0.95 for r in graded)}")
    else:
        print(f"{g}: rows={len(rs)} graded=0")

print("== cost proxy (Claude rows with known tokens)")
mean_by_class = collections.defaultdict(lambda: collections.defaultdict(list))
for g, rs in by.items():
    known = [r for r in rs if r["input_tokens"] != "unknown" and r["model_id"] in PRICE]
    if not known:
        continue
    cost = [proxy(r) for r in known]
    wall = [int(r["wall_s"]) for r in known]
    print(f"{g}: known={len(known)}/{len(rs)} median_wall_s={statistics.median(wall):g} mean_usd={sum(cost)/len(cost):.4f} "
          f"input={sum(int(r['input_tokens']) for r in known)} "
          f"uncached={sum(int(r['input_tokens']) - int(r['cached_input_tokens']) for r in known)} "
          f"output={sum(int(r['output_tokens']) for r in known)}")
    for r, c in zip(known, cost):
        mean_by_class[g][r["task"].split("/")[0]].append(c)


def macro(g, classes):
    return sum(statistics.mean(mean_by_class[g][c]) for c in classes) / len(classes)


seven = [c for c in CLASSES if c != "diagnose-open"]
print("== class-averaged proxy USD per task, 7 classes with every model")
base = macro("claude-haiku-5-5", seven)
for g in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1",
          "haiku + fable plan (worker rows)", "fable plan only"):
    print(f"{g}: {macro(g, seven):.4f}  x{macro(g, seven) / base:.1f} of haiku")
print(f"fable plan + haiku worker: {macro('fable plan only', seven) + macro('haiku + fable plan (worker rows)', seven):.4f}  "
      f"x{(macro('fable plan only', seven) + macro('haiku + fable plan (worker rows)', seven)) / base:.1f} of haiku alone")

print("== external CLIs")
for m in ("gpt-6.1-sol", "kimi-code/k3"):
    rs = [r for r in rows if r["model_id"] == m]
    w = [int(r["wall_s"]) for r in rs]
    line = f"{m}: rows={len(rs)} wall_s min={min(w)} median={statistics.median(w):g} max={max(w)}"
    kn = [r for r in rs if r["input_tokens"] != "unknown"]
    if kn:
        line += (f" input={sum(int(r['input_tokens']) for r in kn)} "
                 f"uncached={sum(int(r['input_tokens']) - int(r['cached_input_tokens']) for r in kn)} "
                 f"output={sum(int(r['output_tokens']) for r in kn)}")
    print(line)

print("== blind judges: task, worker, judgements, mean, per-run range")
js = list(csv.DictReader(open(os.path.join(HERE, "judge_scores.csv"))))
acc = collections.defaultdict(lambda: collections.defaultdict(list))
for r in js:
    worker = r["run_id"].rsplit("-r", 1)[0]
    acc[(r["task"], worker, r["session"])][r["run_id"]].append(int(r["score"]))
for (task, worker, session), runs in sorted(acc.items()):
    all_s = [s for v in runs.values() for s in v]
    per_run = [statistics.mean(v) for v in runs.values()]
    print(f"{task} {worker} {session}: judgements={len(all_s)} mean={statistics.mean(all_s):.2f} "
          f"runs={len(runs)} range={min(per_run):g}-{max(per_run):g}")
pairs = collections.defaultdict(dict)
for r in js:
    if r["session"] == "session1":
        pairs[(r["task"], r["run_id"])][r["judge"]] = int(r["score"])
print("judge disagreement |fable-opus| over", len(pairs), "texts:",
      dict(sorted(collections.Counter(abs(v["fable"] - v["opus"]) for v in pairs.values()).items())))
