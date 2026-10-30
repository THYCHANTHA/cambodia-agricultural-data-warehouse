"""Command line entry point:  python -m cadw.cli {init-db|run|run-without-chirps}"""

from __future__ import annotations

import argparse
import logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cadw", description="Cambodia Agricultural Data Warehouse")
    parser.add_argument("command", choices=["init-db", "run", "run-without-chirps"])
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from . import pipeline

    if args.command == "init-db":
        pipeline.apply_only()
        print("schemas and Bronze tables are in place")
    else:
        pipeline.run_pipeline(skip_chirps=args.command == "run-without-chirps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
