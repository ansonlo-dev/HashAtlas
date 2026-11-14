"""Cache the block sources, pool definitions, network charts and electricity snapshots.

Downloads retry with back-off and reuse cached files. The source manifest records
SHA-256 hashes so later stages can identify the inputs used by a run."""
from __future__ import annotations

import hashlib
import gzip
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from .config import ARTIFACTS, RAW, cfg, ensure_dirs, read_json, write_json

SOLO_POOLS = ["Solo CK", "Bitsolo", "Public Pool", "Braiins Solo", "FutureBit Apollo Solo", "SoloPool.com"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = cfg()["sources"]["user_agent"]
    return s


def _get(s: requests.Session, url: str, tries: int = 5, timeout: int = 60, **kw) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout, **kw)
            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as exc:  # retried with back-off, then re-raised
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url}: {last!r}")


# Block dumps
def _days(first: str, last: str):
    d, end = date.fromisoformat(first), date.fromisoformat(last)
    while d <= end:
        yield d
        d += timedelta(days=1)


def _valid_gz(p: Path) -> bool:
    try:
        with gzip.open(p, "rb") as fh:
            head = fh.readline()
            while fh.read(1 << 20):
                pass
        return head.startswith(b"id\t")
    except (OSError, EOFError):
        return False


def fetch_block_dumps() -> dict:
    c = cfg()["sources"]
    out = RAW / "blockchair_blocks"
    out.mkdir(parents=True, exist_ok=True)
    todo = []
    for d in _days(c["first_day"], c["dumps_last_day"]):
        p = out / f"{d:%Y%m%d}.tsv.gz"
        if not (p.exists() and p.stat().st_size > 0 and _valid_gz(p)):
            todo.append((d, p))
    s = _session()

    def one(d, p):
        r = _get(s, c["blockchair_dump_url"].format(date=f"{d:%Y%m%d}"), timeout=120)
        tmp = p.with_suffix(".part")
        tmp.write_bytes(r.content)
        if not _valid_gz(tmp):
            raise RuntimeError(f"corrupt dump {d}")
        tmp.replace(p)
        return d

    failures = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=c["parallel_downloads"]) as ex:
        futs = {ex.submit(one, d, p): d for d, p in todo}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as exc:  # noqa: BLE001 - recorded and reported; rerun resumes
                failures.append({"day": str(futs[f]), "error": repr(exc)})
            if i % 250 == 0:
                print(f"  dumps {i}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
    files = sorted(out.glob("*.tsv.gz"))
    combined = hashlib.sha256()
    for p in files:
        combined.update(p.name.encode())
        combined.update(sha256_file(p).encode())
    return {"files": len(files), "downloaded_now": len(todo) - len(failures), "failures": failures,
            "combined_sha256": combined.hexdigest(), "seconds": round(time.time() - t0, 1)}


# Mempool.space
def fetch_pool_definitions() -> dict:
    s = _session()
    c = cfg()["sources"]
    r = _get(s, c["pools_definitions_url"])
    (RAW / "pools-v2.json").write_bytes(r.content)
    r2 = _get(s, f"{c['mempool_api']}/mining/pools/all")
    (RAW / "mempool_pools_all.json").write_bytes(r2.content)
    return {"pools_v2_sha256": sha256_bytes(r.content), "pool_list_sha256": sha256_bytes(r2.content),
            "n_definitions": len(r.json()), "n_pools_listed": len(r2.json()["pools"])}


def fetch_solo_blocks() -> dict:
    """Every block mempool.space attributes to a solo-mining service (paginated, 100 per call)."""
    s = _session()
    api = cfg()["sources"]["mempool_api"]
    pools = read_json(RAW / "mempool_pools_all.json")["pools"]
    slug = {p["name"]: p["slug"] for p in pools}
    rows, counts = [], {}
    for name in SOLO_POOLS:
        if name not in slug:
            counts[name] = 0
            continue
        url, seen = f"{api}/mining/pool/{slug[name]}/blocks", set()
        while True:
            batch = _get(s, url).json()
            batch = [b for b in batch if b["height"] not in seen]
            if not batch:
                break
            for b in batch:
                seen.add(b["height"])
                ex = b.get("extras", {})
                rows.append({"height": b["height"], "pool": name, "timestamp": b["timestamp"],
                             "match_rate": ex.get("matchRate"), "coinbase_ascii": ex.get("coinbaseSignatureAscii")})
            url = f"{api}/mining/pool/{slug[name]}/blocks/{min(seen) - 1}"
            time.sleep(0.4)
        counts[name] = len(seen)
    write_json(RAW / "solo_blocks.json", rows)
    return {"solo_blocks": len(rows), "by_service": counts}


def fetch_label_audit(tip_height: int) -> dict:
    """Random sample of mempool.space attributions (15 consecutive blocks per call) to audit our own labels."""
    s = _session()
    c = cfg()["sources"]
    rng = random.Random(cfg()["project"]["random_seed"])
    lo = 560000  # 2019-01-01 is around height 556,000; audit the classification era
    starts = sorted(rng.sample(range(lo, tip_height), c["label_check_samples"]))
    rows = []
    for h in starts:
        for b in _get(s, f"{c['mempool_api']}/blocks/{h}").json():
            rows.append({"height": b["height"], "pool": b.get("extras", {}).get("pool", {}).get("name")})
        time.sleep(0.4)
    write_json(RAW / "label_audit.json", rows)
    return {"audit_blocks": len(rows), "calls": len(starts)}


KEEP_EXTRAS = ["reward", "totalFees", "medianFee", "feeRange", "avgFeeRate", "totalInputs", "totalOutputs",
               "segwitTotalTxs", "segwitTotalSize", "segwitTotalWeight", "coinbaseRaw", "matchRate", "expectedFees"]


def _slim(b: dict) -> dict:
    ex = b.get("extras", {})
    out = {k: b.get(k) for k in ("height", "timestamp", "mediantime", "version", "nonce", "bits", "difficulty",
                                 "tx_count", "size", "weight", "stale")}
    out.update({k: ex.get(k) for k in KEEP_EXTRAS})
    out["pool"] = (ex.get("pool") or {}).get("name")
    return out


def fetch_mempool_blocks(start_height: int) -> dict:
    """Every block from `start_height` to the tip, paginated per mining pool (100 blocks per call).
    mempool.space's own attribution (coinbase tags + payout addresses) becomes the label for this period."""
    import gzip as gz
    import json as js
    api = cfg()["sources"]["mempool_api"]
    pools = read_json(RAW / "mempool_pools_all.json")["pools"]
    out = RAW / "mempool_blocks"
    out.mkdir(parents=True, exist_ok=True)

    def one(p):
        path = out / f"{p['slug']}.jsonl.gz"
        if path.exists():
            return p["slug"], sum(1 for _ in gz.open(path, "rt")), 0
        s = _session()
        url, rows, calls, seen = f"{api}/mining/pool/{p['slug']}/blocks", [], 0, set()
        while True:
            batch = _get(s, url).json()
            calls += 1
            batch = [b for b in batch if b["height"] not in seen]
            if not batch:
                break
            for b in batch:
                seen.add(b["height"])
                if b["height"] >= start_height:
                    rows.append(_slim(b))
            low = min(b["height"] for b in batch)
            if low < start_height:
                break
            url = f"{api}/mining/pool/{p['slug']}/blocks/{low - 1}"
            time.sleep(0.25)
        tmp = path.with_suffix(".part")
        with gz.open(tmp, "wt") as fh:
            for r in rows:
                fh.write(js.dumps(r) + "\n")
        tmp.replace(path)
        return p["slug"], len(rows), calls

    t0, total, calls = time.time(), 0, 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, (slug, n, c) in enumerate(ex.map(one, sorted(pools, key=lambda p: -p["blockCount"])), 1):
            total, calls = total + n, calls + c
            if i % 20 == 0:
                print(f"  pools {i}/{len(pools)} blocks {total} calls {calls} ({time.time() - t0:.0f}s)", flush=True)
    return {"start_height": start_height, "pools": len(pools), "blocks": total, "calls": calls,
            "seconds": round(time.time() - t0, 1)}


def fetch_mempool_heights(heights: list[int]) -> dict:
    """Fill isolated gaps (heights missing from the dumps) with /blocks/{h} (15 blocks ending at h)."""
    import gzip as gz
    import json as js
    api = cfg()["sources"]["mempool_api"]
    s = _session()
    gap_file = RAW / "mempool_gap_blocks.jsonl.gz"
    rows = [js.loads(line) for line in gz.open(gap_file, "rt")] if gap_file.exists() else []
    have = {r["height"] for r in rows}
    need, calls = set(heights) - have, 0
    while need:
        h = max(need)
        batch = _get(s, f"{api}/blocks/{h}").json()
        calls += 1
        for b in batch:
            if b["height"] in need:
                rows.append(_slim(b))
                need.discard(b["height"])
        need.discard(h)
        time.sleep(0.25)
    with gz.open(gap_file, "wt") as fh:
        for r in rows:
            fh.write(js.dumps(r) + "\n")
    return {"gap_blocks": len(rows), "calls": calls}


# Network charts and electricity
def fetch_charts() -> dict:
    s = _session()
    c = cfg()["sources"]
    out = {}
    for chart in c["charts"]:
        r = _get(s, c["blockchain_charts_url"].format(chart=chart))
        (RAW / f"chart_{chart}.json").write_bytes(r.content)
        out[chart] = {"points": len(r.json()["values"]), "sha256": sha256_bytes(r.content)}
        time.sleep(1)
    return out


def fetch_electricity() -> dict:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) HashAtlas-educational"
    url = cfg()["sources"]["electricity_url"]
    html = _get(s, url).text
    (RAW / "electricity_prices.html").write_text(html, encoding="utf-8")
    rows = re.findall(r'<td><a href="/([^/]+)/electricity_prices/"[^>]*>([^<]+)</a></td>\s*<td>([0-9.]*)</td>\s*<td>([0-9.]*)</td>',
                      html)
    data = [{"country": name.strip(), "household_usd_kwh": float(h) if h else None,
             "business_usd_kwh": float(b) if b else None} for _, name, h, b in rows]
    m = re.search(r"(June|March|September|December)[ ,]+(20\d\d)", html)
    write_json(RAW / "electricity_prices.json", {"source": url, "period": m.group(0) if m else None, "rows": data})
    return {"countries": len(data), "period": m.group(0) if m else None, "sha256": sha256_bytes(html.encode())}


def run(parts: list[str] | None = None) -> dict:
    ensure_dirs()
    parts = parts or ["pools", "charts", "electricity", "blocks", "mempool", "gaps", "solo", "audit"]
    man_path = ARTIFACTS / "source_manifest.json"
    manifest = read_json(man_path) if man_path.exists() else {}
    manifest["retrieved_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "pools" in parts:
        manifest["pool_definitions"] = fetch_pool_definitions()
        print("pools:", manifest["pool_definitions"], flush=True)
    if "charts" in parts:
        manifest["charts"] = fetch_charts()
        print("charts ok", flush=True)
    if "electricity" in parts:
        manifest["electricity"] = fetch_electricity()
        print("electricity:", manifest["electricity"], flush=True)
    if "solo" in parts:
        manifest["solo"] = fetch_solo_blocks()
        print("solo:", manifest["solo"], flush=True)
    if "blocks" in parts:
        manifest["block_dumps"] = fetch_block_dumps()
        print("blocks:", {k: v for k, v in manifest["block_dumps"].items() if k != "failures"},
              "failures:", len(manifest["block_dumps"]["failures"]), flush=True)
    if "mempool" in parts:
        manifest["mempool_blocks"] = fetch_mempool_blocks(cfg()["sources"]["mempool_start_height"])
        print("mempool blocks:", manifest["mempool_blocks"], flush=True)
    if "gaps" in parts:
        # heights missing from both the dumps (2009-2018) and the per-pool mempool.space lists (2019+)
        import gzip as gz
        import json as js

        import numpy as np
        import pandas as pd
        start = cfg()["sources"]["mempool_start_height"]
        ids = [x[x < start] for x in (pd.read_csv(p, sep="\t", usecols=["id"])["id"].to_numpy()
                                      for p in sorted((RAW / "blockchair_blocks").glob("*.tsv.gz")))]
        for p in sorted((RAW / "mempool_blocks").glob("*.jsonl.gz")):
            with gz.open(p, "rt") as fh:
                ids.append(np.array([js.loads(line)["height"] for line in fh], dtype=np.int64))
        gap_file = RAW / "mempool_gap_blocks.jsonl.gz"
        if gap_file.exists():
            with gz.open(gap_file, "rt") as fh:
                ids.append(np.array([js.loads(line)["height"] for line in fh], dtype=np.int64))
        have = np.unique(np.concatenate(ids))
        missing = np.setdiff1d(np.arange(0, have.max() + 1), have).tolist()
        manifest["mempool_gaps"] = {"missing_heights": len(missing), **fetch_mempool_heights(missing)}
        print("gaps:", manifest["mempool_gaps"], flush=True)
    if "audit" in parts:
        tip = max(b["height"] for b in read_json(RAW / "solo_blocks.json")) if (RAW / "solo_blocks.json").exists() else 975000
        manifest["label_audit"] = fetch_label_audit(tip)
        print("audit:", manifest["label_audit"], flush=True)
    manifest["sources"] = {k: v for k, v in cfg()["sources"].items() if k.endswith("url") or k.endswith("api")}
    write_json(man_path, manifest)
    return manifest
