"""Command line entry point:  python -m splitfolio run [--fast] [--out DIR]"""

from __future__ import annotations

import argparse
import sys

from .pipeline import run


def main() -> None:
    ap = argparse.ArgumentParser(prog="splitfolio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run all experiments and write the report")
    r.add_argument("--fast", action="store_true", help="reduced sizes for continuous integration")
    r.add_argument("--out", default=None, help="output directory (default: reports/)")
    args = ap.parse_args()
    m = run(out=args.out, fast=args.fast)
    fails = sum(c["status"] == "FAIL" for c in m["checks"])
    print(f"Reports written ({len(m['checks'])} checks, {fails} FAIL)")
    sys.exit(1 if fails and not args.fast else 0)


if __name__ == "__main__":
    main()
