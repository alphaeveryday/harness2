"""Run one serial alpha factory using the three actual upstream forks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..benchmarks.quant import QuantWorkspace
from ..benchmarks.quant_factory import Factory
from ..benchmarks.quant_factory_state import FactoryBusy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autoresearch", type=Path, required=True)
    parser.add_argument("--scientific-skills", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history-file", type=Path, required=True)
    parser.add_argument("--minimum-attempts", type=int, default=100)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.minimum_attempts < 1:
        parser.error("--minimum-attempts must be positive")
    workspace = QuantWorkspace(args.output.resolve(), args.autoresearch.resolve(strict=True),
                               args.scientific_skills.resolve(strict=True))
    factory = Factory(workspace, args.minimum_attempts, args.history_file.resolve(strict=True))
    if args.status:
        print((workspace.output / "status.json").read_text())
        return 0
    try:
        factory.run()
    except FactoryBusy as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BROAD_EXCEPT_OK -- retain CLI boundary failure.
        factory.status("blocked", error=f"{type(error).__name__}: {error}")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
