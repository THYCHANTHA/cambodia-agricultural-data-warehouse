"""Command line entry point:  python -m cadw.cli {init-db|run|run-without-chirps}"""

from __future__ import annotations

import argparse
import logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cadw", description="Cambodia Agricultural Data Warehouse")
    parser.add_argument("command", choices=["init-db", "run"])
    parser.add_argument(
        "--sources", nargs="+", default=None, help="subset of: faostat worldbank boundaries chirps"
    )
    parser.add_argument("--no-dbt", action="store_true", help="skip dbt seed/run/test")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from . import pipeline

    if args.command == "init-db":
        pipeline.apply_only()
        print("schemas and Bronze tables are in place")
    else:
        pipeline.run_pipeline(
            sources=tuple(args.sources) if args.sources else pipeline.ALL_SOURCES,
            with_dbt=not args.no_dbt,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
