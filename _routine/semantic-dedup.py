#!/usr/bin/env python3
"""
加 2 · Kenyalang semantic dedup — flag candidates that repeat recent coverage.

Reads candidates.json, embeds each excerpt, checks cosine similarity against
semantic-seen.json (embeddings of past brief items). Candidates with similarity
≥ THRESHOLD against any past item get "may_be_duplicate: true" added.

Run after fetcher.py, before the brief-writing step.

Usage:
    python3 _routine/semantic-dedup.py

Output:
    candidates.json updated in-place (adds may_be_duplicate field)
    _routine/semantic-seen.json updated with today's accepted items
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
CANDIDATES_PATH = ROOT / "candidates.json"
SEEN_PATH = Path(__file__).parent / "semantic-seen.json"
ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/embeddings"
MODEL = "text-embedding-v3"
THRESHOLD = 0.92       # cosine similarity above this = likely duplicate
RETENTION_DAYS = 14    # keep semantic history for 14 days
BATCH_SIZE = 10


def get_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        try:
            with open(os.path.expanduser("~/.zshrc")) as f:
                for line in f:
                    if "DASHSCOPE_API_KEY" in line and "=" in line:
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except OSError:
            pass
    return key or ""


def embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    body = json.dumps({"model": MODEL, "input": texts, "encoding_format": "float"}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def load_semantic_seen() -> list[dict]:
    if not SEEN_PATH.exists():
        return []
    with open(SEEN_PATH, encoding="utf-8") as f:
        records = json.load(f)
    # Prune old entries
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    return [r for r in records if r.get("date", "") >= cutoff[:10]]


def save_semantic_seen(records: list[dict]) -> None:
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))


def main():
    api_key = get_api_key()
    if not api_key:
        print("semantic-dedup: DASHSCOPE_API_KEY missing — skipping (no duplicate check)")
        sys.exit(0)

    if not CANDIDATES_PATH.exists():
        print("semantic-dedup: candidates.json not found — skipping")
        sys.exit(0)

    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        candidates_data = json.load(f)

    # Collect all candidates across buckets
    all_candidates = []
    for bucket in candidates_data.get("candidates_by_bucket", {}).values():
        all_candidates.extend(bucket)

    if not all_candidates:
        print("semantic-dedup: no candidates — nothing to check")
        sys.exit(0)

    # Build texts to embed (title + excerpt)
    texts = []
    for c in all_candidates:
        title = c.get("title") or c.get("url", "")
        excerpt = (c.get("content_excerpt") or "")[:300]
        texts.append(f"{title}. {excerpt}")

    print(f"semantic-dedup: embedding {len(texts)} candidates...")
    all_vecs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        vecs = embed_batch(batch, api_key)
        all_vecs.extend(vecs)

    # Load past seen embeddings
    seen_records = load_semantic_seen()
    seen_vecs = [r["embedding"] for r in seen_records]

    # Flag duplicates
    flagged = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_records = []

    for candidate, vec in zip(all_candidates, all_vecs):
        is_dup = False
        max_sim = 0.0
        for seen_vec in seen_vecs:
            sim = cosine(vec, seen_vec)
            if sim > max_sim:
                max_sim = sim
            if sim >= THRESHOLD:
                is_dup = True
                break
        candidate["may_be_duplicate"] = is_dup
        candidate["semantic_max_sim"] = round(max_sim, 4)
        if is_dup:
            flagged += 1
        # Always add to new_records (brief generator will decide what to include)
        new_records.append({"date": today, "embedding": vec})

    # Update candidates.json
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(candidates_data, f, ensure_ascii=False, separators=(",", ":"))

    # Update semantic-seen.json (add today's candidates, prune old)
    save_semantic_seen(seen_records + new_records)

    print(f"semantic-dedup: {flagged}/{len(all_candidates)} flagged as possible duplicates (sim ≥ {THRESHOLD})")


if __name__ == "__main__":
    main()
