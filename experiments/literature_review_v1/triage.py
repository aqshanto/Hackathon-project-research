"""
FinCluster Literature Review v1 - triage.

Merges the keyword pool and the snowball pool, deduplicates, and scores every
work against the specific question this review must answer:

    has prior work shown a synthetic workload generator making an
    execution/service-time prediction target degenerate, because the workload
    is determined by a categorical input?

Scoring is a triage aid only. It orders what a human reads; it never decides
inclusion. Every included paper must have its abstract read.

Run from the Research root:
    python experiments\\literature_review_v1\\triage.py [N]

Output:
    literature/triage_ranked.csv
    stdout: top N with abstract snippets for screening
"""

import csv
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# (weight, pattern) - the higher the weight, the closer to the review question
SIGNALS = [
    # the exact phenomenon
    (6, r"trivial baseline|simple baseline|naive baseline|lookup table"),
    (6, r"degenerate|spurious (correlation|regression|feature)|shortcut learn"),
    (5, r"(does not|fail(s|ed)? to) outperform|outperform(s|ed)? (the )?(deep|learned|ml|machine)"),
    (5, r"cost model"),
    # the task
    (4, r"(execution|runtime|response|service|completion|job|query) time predict"),
    (4, r"predict(ing|ion of)? (the )?(execution|runtime|response|service|tail) (time|latency)"),
    (3, r"performance prediction|latency prediction|runtime prediction"),
    # benchmark construction and validity
    (4, r"synthetic (workload|benchmark|data) generat"),
    (3, r"benchmark (design|validity|construction)|measurement methodolog"),
    (3, r"reproducib|experiment(al)? (design|validity)|internal validity"),
    (3, r"data leakage|target leakage|feature leakage"),
    # the environment
    (3, r"cgroup|cfs quota|cpu quota|throttl"),
    (2, r"container|docker|kubernetes|virtual machine|hypervisor"),
    (2, r"interference|co-locat|colocat|noisy neighbou?r|contention"),
    (2, r"heterogeneous (node|server|processor|hardware)"),
    # routing / scheduling use
    (2, r"load balanc|request routing|task placement|scheduling polic"),
    (2, r"round robin|least loaded|shortest queue|queue(ing)? (delay|wait|length)"),
    (1, r"payment|transaction|financial"),
]

PENALTIES = [
    (-8, r"tumou?r|cancer|clinical|patient|medical imag|radiolog|histopath|"
         r"retinop|eeg|ecg|covid|drug|molecul|protein|genom"),
    (-6, r"crop|agricultur|soil|weather|climate|rainfall|hydrolog|seismic|"
         r"astronom|galax|pig farming|biogas"),
    (-6, r"student|education|classroom|curriculum|pedagog"),
    (-4, r"deepfake|face recognition|speech synthesis|text-to-speech|"
         r"sentiment|translation|recommend(er|ation) system"),
]


def score(row):
    text = ((row.get("title") or "") + " " + (row.get("abstract") or "")).lower()
    if not text.strip():
        return -99, []
    total, hits = 0, []
    for weight, pat in SIGNALS:
        if re.search(pat, text):
            total += weight
            hits.append(pat.split("|")[0][:22])
    for weight, pat in PENALTIES:
        if re.search(pat, text):
            total += weight
    # a work with no abstract cannot be screened properly
    if not (row.get("abstract") or "").strip():
        total -= 5
    return total, hits


def main():
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    here = os.path.dirname(os.path.abspath(__file__))
    lit = os.path.join(os.path.dirname(os.path.dirname(here)), "literature")

    pool, seen, seen_titles = [], set(), set()
    for name, origin in (("candidates.csv", "keyword"),
                         ("snowball_pool.csv", "snowball")):
        path = os.path.join(lit, name)
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            wid = r.get("openalex_id", "")
            norm = "".join(c.lower() for c in (r.get("title") or "") if c.isalnum())
            if not wid or wid in seen or not norm or norm in seen_titles:
                continue
            seen.add(wid)
            seen_titles.add(norm)
            r.setdefault("origin", origin)
            pool.append(r)

    for r in pool:
        s, hits = score(r)
        r["score"] = s
        r["signals"] = ";".join(hits[:6])

    pool.sort(key=lambda r: (-r["score"], -int(r.get("cited_by") or 0)))

    fields = ["score", "signals", "origin", "openalex_id", "doi", "title",
              "year", "venue", "cited_by", "oa_status", "oa_url", "abstract"]
    with open(os.path.join(lit, "triage_ranked.csv"), "w",
              newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        wri.writeheader()
        wri.writerows(pool)

    print("POOL_SIZE = %d" % len(pool))
    print("SCORE >= 12 : %d" % sum(1 for r in pool if r["score"] >= 12))
    print("SCORE >= 8  : %d" % sum(1 for r in pool if r["score"] >= 8))
    print("")
    for i, r in enumerate(pool[:top_n], 1):
        ab = re.sub(r"\s+", " ", r.get("abstract") or "")[:300]
        print("[%3d] s=%-3s %s | %s | %s | cited %s" % (
            i, r["score"], r["year"], r["title"][:78],
            (r["venue"] or "-")[:34], r["cited_by"]))
        print("      %s" % (ab or "(no abstract)"))
        print("")


if __name__ == "__main__":
    main()
