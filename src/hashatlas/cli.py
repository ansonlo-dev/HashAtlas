"""Command-line entry point: `uv run hashatlas <stage>` (see README for the stage order)."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time

from .config import ARTIFACTS, read_json, write_json

STAGES = ["acquire", "clean", "features", "train", "evaluate", "explain", "clusters", "rules",
          "decide", "future", "figures", "webdata", "verify", "report", "notebook"]


def _log(stage: str, seconds: float) -> None:
    p = ARTIFACTS / "run_log.json"
    log = read_json(p) if p.exists() else {}
    log[stage] = {"seconds": round(seconds, 1), "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    write_json(p, log)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="hashatlas", description="HashAtlas data-mining pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--parts", nargs="*", default=None, help="pools charts electricity blocks solo audit")
    for s in STAGES[1:]:
        sub.add_parser(s)
    sub.add_parser("run-all")
    p = sub.add_parser("predict", help="score new blocks (heights) or a miner set-up")
    p.add_argument("--heights", nargs="*", type=int, default=None)
    p.add_argument("--ths", type=float, default=None, help="miner hash rate in TH/s")
    p.add_argument("--watts", type=float, default=None)
    p.add_argument("--country", default="Hong Kong")
    p.add_argument("--price", type=float, default=None, help="BTC price assumption in USD (default: last observed)")
    args = ap.parse_args(argv)

    if args.cmd == "acquire":
        from . import acquire
        t0 = time.time()
        acquire.run(args.parts)
        _log("acquire", time.time() - t0)
        return
    if args.cmd == "predict":
        from . import predict
        print(json.dumps(predict.run(args), indent=1, ensure_ascii=False))
        return
    stages = STAGES[1:] if args.cmd == "run-all" else [args.cmd]
    for st in stages:
        t0 = time.time()
        print(f"== {st}", flush=True)
        importlib.import_module(f".{st}", __package__).run()
        _log(st, time.time() - t0)


if __name__ == "__main__":
    main(sys.argv[1:])
