"""Deterministic A/B for the data-query set (duckdb): targeted-query vs whole-file Read.

tiktoken cl100k both lanes (same encoder => relative delta valid). No ccusage/session.

Workload = 3 question classes on ONE fixed CSV:
  Q1 count-by-group   Q2 filter+project   Q3 aggregate (avg/sum)
Lane A = the agent Reads the WHOLE file into context, then reasons over rows.
Lane B = `duckdb -c "<SQL>"` returns ONLY the answer slice. Includes the honest
         one-time schema-discovery cost (`DESCRIBE SELECT * ...`) — the data-file
         analogue of the discovery objection (cheap + bounded, unlike a web fetch).

Usage: py bench/_dataquery_ab.py [--rows 50000]
Fixture auto-generated deterministically at bench/out/dq_sales.csv if absent.
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("cl100k_base")
OUT = Path("bench/out")
CSV = OUT / "dq_sales.csv"


def toks(text: str) -> int:
    return len(ENC.encode(text))


def _duckdb() -> str:
    p = shutil.which("duckdb")
    if p:
        return p
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / (
        "Microsoft/WinGet/Packages/DuckDB.cli_Microsoft.Winget.Source_8wekyb3d8bbwe/duckdb.exe"
    )
    return str(cand) if cand.exists() else "duckdb"


DUCKDB = _duckdb()


def duck(sql: str) -> str:
    p = subprocess.run([DUCKDB, "-c", sql], capture_output=True, text=True, encoding="utf-8")
    return (p.stdout or "") + (p.stderr or "")


def gen_csv(rows: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)  # deterministic
    regions = ["north", "south", "east", "west", "central"]
    products = [f"SKU-{i:03d}" for i in range(120)]
    lines = ["order_id,order_date,region,product,qty,unit_price"]
    for oid in range(1, rows + 1):
        d = f"2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        lines.append(
            f"{oid},{d},{rng.choice(regions)},{rng.choice(products)},"
            f"{rng.randint(1,40)},{rng.randint(5,500)}.{rng.randint(0,99):02d}"
        )
    CSV.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    rows = 50000
    for i, a in enumerate(argv):
        if a == "--rows":
            rows = int(argv[i + 1])
    if not CSV.exists():
        gen_csv(rows)
    raw = CSV.read_text(encoding="utf-8")
    size_mb = len(raw.encode("utf-8")) / 1e6
    f = str(CSV).replace("\\", "/")

    print(f"# data-query A/B  fixture={f}  {size_mb:.2f} MB  {raw.count(chr(10))} rows\n")

    laneA = toks(raw)
    print(f"## Lane A — Read whole file into context = {laneA} tok\n")

    schema = duck(f"DESCRIBE SELECT * FROM '{f}'")
    schema_t = toks(schema)
    queries = {
        "Q1 count by region": f"SELECT region, count(*) c FROM '{f}' GROUP BY 1 ORDER BY 2 DESC",
        "Q2 top-5 orders qty>35 in west": (
            f"SELECT order_id, product, qty, unit_price FROM '{f}' "
            f"WHERE qty>35 AND region='west' ORDER BY qty DESC LIMIT 5"
        ),
        "Q3 revenue by region": (
            f"SELECT region, round(sum(qty*unit_price),2) rev FROM '{f}' GROUP BY 1 ORDER BY 2 DESC"
        ),
    }
    print(f"## Lane B — duckdb targeted queries (schema-discovery once = {schema_t} tok)")
    total_b = schema_t
    for label, sql in queries.items():
        t = toks(duck(sql))
        total_b += t
        print(f"  {label:34s} = {t} tok")
    print(f"\nLane B TOTAL (schema + 3 answers) = {total_b} tok")
    print(f"\ndelta = {100*(laneA-total_b)/laneA:+.2f}%  (B vs A; whole-file Read avoided)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
