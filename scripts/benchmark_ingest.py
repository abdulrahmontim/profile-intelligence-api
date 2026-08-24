"""
Benchmark harness for the /api/profiles/import ingestion endpoint.

Generates (or reuses) a synthetic CSV, authenticates, uploads with wall-time
and server-memory sampling, verifies the resulting row count via the API,
and prints a markdown table row for documentation.

Usage examples:
    python scripts/benchmark_ingest.py --rows 500000 --label "fresh insert"
    python scripts/benchmark_ingest.py --rows 500000 --no-gen --label "re-upload (dedup)"
"""

import argparse
import csv
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from urllib.parse import urlparse

import requests

FIRST = ["ada", "chidi", "amina", "tunde", "zainab", "emeka", "folake", "ibrahim",
         "ngozi", "sade", "yusuf", "chioma", "bola", "kemi", "obi", "hauwa"]
LAST = ["okafor", "bello", "adeyemi", "musa", "eze", "lawal", "danhassan",
        "nwosu", "oluwaseun", "abubakar", "chukwu", "balogun", "usman", "adesina"]
COUNTRIES = [("NG", "Nigeria"), ("US", "United States"), ("GB", "United Kingdom"),
             ("DE", "Germany"), ("IN", "India"), ("BR", "Brazil")]
AGE_GROUPS = [(0, 12, "child"), (13, 19, "teenager"), (20, 59, "adult"), (60, 90, "senior")]


def generate_csv(path, rows):
    rng = random.Random(42)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "gender", "age", "age_group", "country_id",
                    "country_name", "gender_probability", "country_probability"])
        for i in range(rows):
            lo, hi, group = rng.choice(AGE_GROUPS)
            cid, cname = rng.choice(COUNTRIES)
            w.writerow([f"{rng.choice(FIRST)} {rng.choice(LAST)} {i}",
                        rng.choice(["male", "female"]),
                        rng.randint(lo, hi), group, cid, cname,
                        round(rng.uniform(0.5, 0.99), 2),
                        round(rng.uniform(0.1, 0.9), 2)])
            if (i + 1) % 100_000 == 0:
                print(f"  generated {i + 1:,}/{rows:,}")
    return os.path.getsize(path) / 1e6


def get_token(base):
    r = requests.get(f"{base}/auth/github/callback",
                     params={"code": "test_code"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def get_server_pid(port):
    out = subprocess.check_output(["netstat", "-ano"], text=True)
    for line in out.splitlines():
        if f":{port} " in line and "LISTENING" in line.upper():
            return line.split()[-1]
    return None


class MemorySampler:
    def __init__(self, pid, interval=1.0):
        self.pid, self.interval = pid, interval
        self.peak_kb = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _sample_kb(self):
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {self.pid}", "/FO", "CSV", "/NH"], text=True)
            m = re.findall(r'"(\d[\d,]*)\s*K"', out)
            return int(m[0].replace(",", "")) if m else 0
        except Exception:
            return 0

    def _run(self):
        while not self._stop.is_set():
            kb = self._sample_kb()
            if kb > self.peak_kb:
                self.peak_kb = kb
            time.sleep(self.interval)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=500_000)
    ap.add_argument("--out", default="loadtest.csv")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--label", default="import")
    ap.add_argument("--no-gen", action="store_true",
                    help="reuse existing --out file (for dedup/re-upload runs)")
    ap.add_argument("--expect-total", type=int,
                    help="verify GET /api/profiles total equals this after import")
    args = ap.parse_args()

    # 1. file
    if args.no_gen:
        mb = os.path.getsize(args.out) / 1e6
        n = sum(1 for _ in open(args.out, encoding="utf-8")) - 1
        print(f"Reusing {args.out}: {n:,} rows, {mb:.1f} MB")
    else:
        print("Generating CSV...")
        n = args.rows
        mb = generate_csv(args.out, args.rows)
        print(f"Wrote {args.out}: {n:,} rows, {mb:.1f} MB")

    # 2. auth
    token = get_token(args.base)
    headers = {"Authorization": f"Bearer {token}", "X-API-Version": "1"}
    print("Authenticated.")

    # 3. server pid for memory sampling
    port = urlparse(args.base).port or 80
    pid = get_server_pid(port)
    print(f"Server PID: {pid}" if pid else "WARNING: PID not found, no memory stats")

    # 4. timed upload with memory sampling + heartbeat
    hb_stop = threading.Event()

    def heartbeat():
        start = time.perf_counter()
        while not hb_stop.wait(15):
            print(f"  ...upload in progress ({time.perf_counter() - start:.0f}s elapsed), "
                  f"watch server terminal for [import] ticks")

    t0 = time.perf_counter()
    threading.Thread(target=heartbeat, daemon=True).start()
    with ExitStack() as stack:
        fh = stack.enter_context(open(args.out, "rb"))
        sampler = stack.enter_context(MemorySampler(pid)) if pid else None
        resp = requests.post(f"{args.base}/api/profiles/import", headers=headers,
                             files={"file": (args.out, fh, "text/csv")}, timeout=3600)
    hb_stop.set()
    elapsed = time.perf_counter() - t0

    print(f"\nHTTP {resp.status_code}")
    body = resp.json()
    print(json.dumps(body, indent=2))

    if resp.status_code != 200:
        sys.exit("Import failed - aborting.")

    inserted = body.get("inserted", 0)
    skipped = body.get("skipped", 0)

    # 5. optional row-count verification through the public API
    verified = None
    if args.expect_total is not None:
        v = requests.get(f"{args.base}/api/profiles",
                         params={"page": 1, "limit": 1}, headers=headers, timeout=60)
        verified = v.json().get("total")
        match = "OK" if verified == args.expect_total else "MISMATCH!"
        print(f"\nAPI total={verified:,} (expected {args.expect_total:,}) {match}")

    peak_mb = (sampler.peak_kb / 1024) if pid and sampler else None

    # 6. report
    print("\n--- SUMMARY ---")
    print(f"label={args.label} | rows={n:,} | {mb:.1f}MB | {elapsed:.1f}s | "
          f"{int(n / elapsed):,}/s | peak_mem="
          + (f"{peak_mb:.0f}MB" if peak_mb else "n/a")
          + f" | inserted={inserted:,} | skipped={skipped:,}")

    print("\n--- MARKDOWN ROW ---")
    mem = f"{peak_mb:.0f}" if peak_mb else "n/a"
    print(f"| {args.label} | {n:,} | {mb:.1f} | {elapsed:.1f}s | "
          f"{int(n / elapsed):,}/s | {mem} | {inserted:,} | {skipped:,} |")


if __name__ == "__main__":
    main()
