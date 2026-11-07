"""Reproduce frozen forecast paths, paired temporal ranges and stock-policy replay."""

import argparse
import gzip
import json
from pathlib import Path

from grd.benchmark import ASSETS
from grd.evaluation import bootstrap_report, inventory_report, paths_from_source, save_json, save_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ASSETS)
    parser.add_argument("--reuse-paths", type=Path)
    parser.add_argument("--seeds", type=int, default=200)
    args = parser.parse_args()
    if args.seeds < 200:
        parser.error("Published evaluation requires at least 200 paired logistics seeds")
    args.output.mkdir(parents=True, exist_ok=True)
    report = json.loads((ASSETS / "pharma-benchmark.json").read_text())
    archive = json.loads(gzip.decompress(args.reuse_paths.read_bytes())) if args.reuse_paths else paths_from_source(ASSETS / "pharma-salesdaily.csv", report)
    if archive["source_sha256"] != report["sha256"]:
        raise ValueError("Prediction paths use a different source CSV")
    save_paths(args.output / "pharma-backtest-paths.json.gz", archive)
    save_json(args.output / "pharma-evaluation.json", bootstrap_report(archive, report))
    save_json(args.output / "pharma-inventory-replay.json", inventory_report(archive, args.seeds))
    print("Saved reproducible final evidence; no measured company impact claimed", flush=True)


if __name__ == "__main__":
    main()
