"""
FinCluster Literature Review v1 - candidate harvesting.

Queries the OpenAlex works API across four literature clusters and writes a
de-duplicated candidate list for abstract-level screening.

OpenAlex is used instead of an arXiv-only pull because the relevant work for
this project sits largely in conference and journal venues (USENIX, SoCC,
EuroSys, ICDE, VLDB) that arXiv does not index. Standard library only - no
pip install required.

No personal identifiers are sent. The request uses the OpenAlex common pool
rather than the polite pool, which is slower but requires no email.

Run from the Research root:
    python experiments\\literature_review_v1\\fetch_candidates.py

Output:
    literature/candidates.csv
    literature/fetch_manifest.json
"""

import csv
import json
import sys
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.openalex.org/works"
PER_PAGE = 25
SLEEP_BETWEEN = 1.1          # be gentle on the shared pool
FROM_YEAR = 2012             # ICDE 2013 cost-model paper is a key precedent

# Four clusters. Each query is deliberately narrow: broad queries return
# thousands of loosely-related works and waste screening attention.
CLUSTERS = {
    "C1_container_perf": [
        "container CPU quota throttling performance",
        "cgroup CPU bandwidth container",
        "CPU throttling containerized application latency",
        "performance interference co-located containers",
        "cloud performance variability reproducible benchmarking",
        "docker container performance isolation measurement",
    ],
    "C2_time_prediction": [
        "query execution time prediction machine learning",
        "microservice tail latency prediction",
        "service time prediction heterogeneous nodes",
        "job runtime prediction cluster scheduling machine learning",
    ],
    "C3_degeneracy": [
        "shortcut learning spurious feature benchmark",
        "simple baseline outperforms machine learning systems",
        "synthetic workload generation benchmark validity",
        "negative results machine learning evaluation pitfalls",
    ],
    "C4_routing": [
        "load balancing predicted response time routing policy",
        "payment transaction routing optimization machine learning",
        "learning based request routing heterogeneous servers",
    ],
}

FIELDS = [
    "cluster", "query", "rank", "openalex_id", "doi", "title", "year", "venue",
    "type", "cited_by", "oa_status", "oa_url", "abstract",
]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def reconstruct_abstract(inverted):
    """OpenAlex stores abstracts as an inverted index; rebuild the text."""
    if not inverted:
        return ""
    positions = []
    for word, idxs in inverted.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    text = " ".join(w for _, w in positions)
    return text[:1500]


def fetch(query):
    # title_and_abstract.search requires every term to appear in the title or
    # abstract. The plain `search` parameter also matches full text and returns
    # topically unrelated high-citation works (brain tumour segmentation,
    # climate models) for systems queries.
    params = {
        "per-page": str(PER_PAGE),
        "filter": "from_publication_date:%d-01-01,primary_topic.field.id:fields/17,"
                  "title_and_abstract.search:%s" % (FROM_YEAR, query),
        "sort": "relevance_score:desc",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "FinCluster-litreview/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    research_root = os.path.dirname(os.path.dirname(here))
    out_dir = os.path.join(research_root, "literature")
    os.makedirs(out_dir, exist_ok=True)

    seen = set()
    seen_titles = set()
    rows = []
    log = []

    for cluster, queries in CLUSTERS.items():
        for q in queries:
            try:
                data = fetch(q)
            except Exception as exc:                      # noqa: BLE001
                print("  FAILED  %-52s %s" % (q[:52], exc))
                log.append({"cluster": cluster, "query": q, "error": str(exc)})
                continue

            results = data.get("results", [])
            kept = 0
            for rank, w in enumerate(results, 1):
                wid = w.get("id", "")
                if not wid or wid in seen:
                    continue
                norm = "".join(ch.lower() for ch in (w.get("title") or "") if ch.isalnum())
                if not norm or norm in seen_titles:
                    continue
                seen.add(wid)
                seen_titles.add(norm)

                loc = w.get("primary_location") or {}
                src = loc.get("source") or {}
                oa = w.get("open_access") or {}

                rows.append({
                    "cluster": cluster,
                    "query": q,
                    "rank": rank,
                    "openalex_id": wid.rsplit("/", 1)[-1],
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": (w.get("title") or "").replace("\n", " "),
                    "year": w.get("publication_year") or "",
                    "venue": src.get("display_name") or "",
                    "type": w.get("type") or "",
                    "cited_by": w.get("cited_by_count") or 0,
                    "oa_status": oa.get("oa_status") or "",
                    "oa_url": oa.get("oa_url") or "",
                    "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
                })
                kept += 1

            print("  %-18s %-52s %2d new / %2d" % (cluster, q[:52], kept, len(results)))
            log.append({"cluster": cluster, "query": q,
                        "returned": len(results), "new": kept})
            time.sleep(SLEEP_BETWEEN)

    rows.sort(key=lambda r: (r["cluster"], int(r["rank"])))

    csv_path = os.path.join(out_dir, "candidates.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    oa_count = sum(1 for r in rows if r["oa_url"])
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": "OpenAlex works API",
        "from_publication_year": FROM_YEAR,
        "per_page": PER_PAGE,
        "clusters": {c: len(qs) for c, qs in CLUSTERS.items()},
        "total_unique_works": len(rows),
        "with_open_access_url": oa_count,
        "per_cluster": {
            c: sum(1 for r in rows if r["cluster"] == c) for c in CLUSTERS
        },
        "query_log": log,
    }
    with open(os.path.join(out_dir, "fetch_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print("")
    print("TOTAL_UNIQUE_WORKS = %d" % len(rows))
    print("WITH_OPEN_ACCESS_URL = %d" % oa_count)
    for c in CLUSTERS:
        print("  %-18s %d" % (c, manifest["per_cluster"][c]))
    print("WROTE %s" % csv_path)


if __name__ == "__main__":
    main()
