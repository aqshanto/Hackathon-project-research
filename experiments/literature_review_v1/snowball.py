"""
FinCluster Literature Review v1 - citation snowballing.

Keyword search reached the container-performance (C1) and execution-time
prediction (C2) literature well, but missed C3/C4 almost entirely. This pass
expands from confirmed on-target seed papers in both directions:

    backward  - works the seed cites   (referenced_works)
    forward   - works that cite the seed (filter=cites:<id>)

Snowballing is the standard remedy when a topic has no single vocabulary,
which is the case here: the same idea is called cost model calibration in
databases, interference prediction in cloud systems, and shortcut learning
in ML.

Standard library only. Run from the Research root:
    python experiments\\literature_review_v1\\snowball.py

Output:
    literature/snowball_pool.csv     - seed-expanded pool, deduplicated
    literature/snowball_manifest.json
"""

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "https://api.openalex.org/works"
SLEEP = 1.1
FORWARD_LIMIT = 50          # citing works pulled per seed

# Seeds confirmed on-target by reading titles/abstracts in Stage 1.
# Matched against candidates.csv by case-insensitive title prefix.
SEED_TITLES = [
    # C2 - execution/service-time prediction (the closest neighbours)
    "Predicting query execution time: Are optimizer cost models really unusable",
    "Same Queries, Different Data: Can We Predict Runtime Performance",
    "Towards predicting query execution time for concurrent and dynamic database",
    "Predicting the End-to-End Tail Latency of Containerized Microservices",
    "Runtime prediction of parallel applications with workload-aware clustering",
    # C1 - container performance / interference
    "Interference Analysis of Co-Located Container Workloads",
    "Rusty: Runtime Interference-Aware Predictive Monitoring",
    "KVM, Xen and Docker: A performance analysis",
    # C3 - degeneracy, only where it touches systems/regression
    "Shortcut to Nowhere: Demystifying Deep Spurious Regression",
    "SynQL: A Controllable and Scalable Rule-Based Framework",
]

FIELDS = ["origin", "seed", "direction", "openalex_id", "doi", "title", "year",
          "venue", "type", "cited_by", "oa_status", "oa_url", "abstract"]


def get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "FinCluster-litreview/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def reconstruct_abstract(inv):
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    return " ".join(w for _, w in pos)[:1500]


def row_from_work(w, seed, direction):
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    oa = w.get("open_access") or {}
    return {
        "origin": "snowball",
        "seed": seed[:48],
        "direction": direction,
        "openalex_id": (w.get("id") or "").rsplit("/", 1)[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
        "title": (w.get("title") or "").replace("\n", " "),
        "year": w.get("publication_year") or "",
        "venue": src.get("display_name") or "",
        "type": w.get("type") or "",
        "cited_by": w.get("cited_by_count") or 0,
        "oa_status": oa.get("oa_status") or "",
        "oa_url": oa.get("oa_url") or "",
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    lit = os.path.join(root, "literature")

    existing = list(csv.DictReader(
        open(os.path.join(lit, "candidates.csv"), encoding="utf-8")))
    by_title = {r["title"].lower(): r for r in existing}

    seeds = []
    for want in SEED_TITLES:
        hit = None
        for t, r in by_title.items():
            if t.startswith(want.lower()[:55]):
                hit = r
                break
        if hit:
            seeds.append((hit["openalex_id"], hit["title"]))
            print("  SEED  %s  %s" % (hit["openalex_id"], hit["title"][:64]))
        else:
            print("  MISS  %s" % want[:64])

    seen = {r["openalex_id"] for r in existing}
    seen_titles = {"".join(c.lower() for c in r["title"] if c.isalnum())
                   for r in existing}
    rows = []
    log = []

    for sid, stitle in seeds:
        # --- backward: what this paper cites ---
        back = 0
        try:
            work = get("%s/%s" % (API, sid))
            refs = [r.rsplit("/", 1)[-1] for r in (work.get("referenced_works") or [])]
            time.sleep(SLEEP)
            for i in range(0, len(refs), 40):
                chunk = refs[i:i + 40]
                url = "%s?filter=openalex_id:%s&per-page=40" % (
                    API, "|".join(chunk))
                data = get(url)
                for w in data.get("results", []):
                    wid = (w.get("id") or "").rsplit("/", 1)[-1]
                    norm = "".join(c.lower() for c in (w.get("title") or "") if c.isalnum())
                    if not wid or wid in seen or not norm or norm in seen_titles:
                        continue
                    seen.add(wid)
                    seen_titles.add(norm)
                    rows.append(row_from_work(w, stitle, "backward"))
                    back += 1
                time.sleep(SLEEP)
        except Exception as exc:                                # noqa: BLE001
            print("  backward FAILED %s: %s" % (sid, exc))

        # --- forward: what cites this paper ---
        fwd = 0
        try:
            url = "%s?filter=cites:%s&per-page=%d&sort=cited_by_count:desc" % (
                API, sid, FORWARD_LIMIT)
            data = get(url)
            for w in data.get("results", []):
                wid = (w.get("id") or "").rsplit("/", 1)[-1]
                norm = "".join(c.lower() for c in (w.get("title") or "") if c.isalnum())
                if not wid or wid in seen or not norm or norm in seen_titles:
                    continue
                seen.add(wid)
                seen_titles.add(norm)
                rows.append(row_from_work(w, stitle, "forward"))
                fwd += 1
            time.sleep(SLEEP)
        except Exception as exc:                                # noqa: BLE001
            print("  forward FAILED %s: %s" % (sid, exc))

        print("  %-58s back %3d  fwd %3d" % (stitle[:58], back, fwd))
        log.append({"seed": stitle, "openalex_id": sid,
                    "backward_new": back, "forward_new": fwd})

    out = os.path.join(lit, "snowball_pool.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wri = csv.DictWriter(fh, fieldnames=FIELDS)
        wri.writeheader()
        wri.writerows(rows)

    with open(os.path.join(lit, "snowball_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "seeds_found": len(seeds),
            "seeds_missing": len(SEED_TITLES) - len(seeds),
            "new_unique_works": len(rows),
            "per_seed": log,
        }, fh, indent=2)

    print("")
    print("SEEDS_USED = %d / %d" % (len(seeds), len(SEED_TITLES)))
    print("NEW_UNIQUE_WORKS = %d" % len(rows))
    print("WROTE %s" % out)


if __name__ == "__main__":
    main()
