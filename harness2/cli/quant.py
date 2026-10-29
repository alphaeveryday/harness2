"""Run the original Harness² method on the forked Quant autoresearch profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..benchmarks.quant import QuantAdapter, QuantWorkspace
from ..core.proposer import Proposer
from ..core.schedule import mode_token, run_domain


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autoresearch", type=Path, required=True)
    parser.add_argument("--scientific-skills", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-file", type=Path, required=True)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--mode", choices=("parallel", "sequential"), default="sequential")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be positive")
    workspace = QuantWorkspace(args.output.resolve(), args.autoresearch.resolve(strict=True),
                               args.scientific_skills.resolve(strict=True))
    adapter = QuantAdapter(workspace, args.task_file.read_text(encoding="utf-8"))
    if args.prepare_only:
        print(json.dumps({"base_harness": str(adapter.base_harness()), "model_calls": 0}))
        return 0
    proposer = Proposer(adapter.spec.channels["proposer"],
                        audit_dir=workspace.output / "model-audit", attempts=1)
    result = run_domain("daily-equities", adapter.tasks(), args.k, adapter=adapter,
                        prop=proposer, runs_root=adapter.spec.runs_root,
                        library_root=workspace.output / "library",
                        modes=(mode_token(args.mode),))
    result["execution_count"] = adapter.execution_count
    result["investment_promotion"] = False
    (workspace.output / "quant.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
