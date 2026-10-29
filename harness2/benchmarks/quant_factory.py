"""One durable supervisor; each native Harness² task addresses one hypothesis."""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from ..core.library import Library
from ..core.proposer import Proposer
from ..core.schedule import run_task
from .quant import QuantAdapter, QuantWorkspace
from .quant_factory_author import author
from .quant_factory_notify import notify
from .quant_factory_state import (
    Attempt,
    FactoryBusy,
    FactoryError,
    atomic_json,
    behavior_hash,
    finish,
    history,
    source_hash,
)


@dataclass(frozen=True, slots=True)
class Factory:
    workspace: QuantWorkspace
    minimum: int
    inherited: Path

    def status(self, phase: str, current: Path | None = None, error: str = "") -> None:
        root = self.workspace.output
        attempts = history(root)
        payload = {"phase": phase, "completed_new_candidates": sum(a.counted for a in attempts),
                   "recorded_attempts": len(attempts), "minimum": self.minimum,
                   "current": str(current) if current else None, "pid": os.getpid(),
                   "at": datetime.now(timezone.utc).isoformat(), "error": error,
                   "investment_promotion": False}
        atomic_json(root / "status.json", json.dumps(payload, indent=2))
        print(json.dumps(payload), flush=True)
        notify(root, phase, sum(a.counted for a in attempts), self.minimum, error)

    def run(self) -> None:
        root = self.workspace.output
        root.mkdir(parents=True, exist_ok=True)
        study = Path(os.environ["QUANTLAB_HOME"]).resolve(strict=True)
        if root.resolve().is_relative_to(study):
            raise FactoryError("Factory output must be outside the inherited study")
        lock_path = study / ".local/autoresearch/factory.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise FactoryBusy("Another factory owns this study") from exc
            engine = Path(os.environ["QUANTLAB_REPO"]).resolve(strict=True)
            self._freeze_inputs(engine, study)
            attempts = history(root)
            while sum(item.counted for item in attempts) < self.minimum:
                if (root / "STOP").exists():
                    self.status("stopped")
                    return
                directory = root / "attempts" / f"{len(attempts) + 1:06d}"
                directory.mkdir(parents=True, exist_ok=True)
                self.status("authoring", directory)
                self._one(directory, engine, study, attempts)
                attempts = history(root)
                failures = [a.status for a in attempts[-2:]]
                if len(failures) == 2 and all(s in {"preflight_failed", "crash", "duplicate", "duplicate_pnl"} for s in failures):
                    raise FactoryError("Two consecutive invalid/duplicate attempts; inspect before continuing")
            self.status("completed")

    def _freeze_inputs(self, engine: Path, study: Path) -> None:
        root = self.workspace.output
        paths = [self.inherited, Path(os.environ["QUANTLAB_PROTOCOL"]),
                 *sorted((self.workspace.autoresearch / "quant").glob("*.py")),
                 self.workspace.autoresearch / "quant/program.md",
                 *sorted((engine / "quantlab").rglob("*.py")),
                 *sorted((engine / "scripts").glob("*.py")),
                 engine / "scripts/assessment_policy.json", engine / "uv.lock",
                 *sorted(Path(__file__).parents[1].rglob("*.py"))]
        for skill in ("hypothesis-generation", "scientific-critical-thinking", "statistical-analysis"):
            paths.extend(p for p in (self.workspace.scientific_skills / "skills" / skill).rglob("*")
                         if p.is_file() and "__pycache__" not in p.parts)
        payload = {"files": {str(path): source_hash(path) for path in paths}, "study": str(study),
                   "minimum": self.minimum}
        manifest = root / "factory-inputs.json"
        if manifest.exists() and json.loads(manifest.read_text()) != payload:
            raise FactoryError("Factory code/inputs changed; inspect and use a new run namespace")
        atomic_json(manifest, json.dumps(payload, indent=2))

    def _one(self, directory: Path, engine: Path, study: Path, attempts: list[Attempt]) -> None:
        candidate, hypothesis = author(directory, self.workspace, engine, attempts, self.inherited.read_text())
        digest, behavior = source_hash(candidate), behavior_hash(candidate)
        prior = [*sorted((study / "runs").glob("*/alpha.py")), *sorted((engine / "alphas").glob("*.py"))]
        known = {item.behavior_hash for item in attempts}
        known.update(behavior_hash(path) for path in prior)
        evaluation = directory / "evaluation"
        # A saved evaluation of this same sealed attempt is a resume, not a new proposal.
        own_result = evaluation / "result.json"
        if behavior in known and not own_result.exists():
            finish(directory, Attempt(str(directory), digest, behavior, "", False, "duplicate",
                                      hypothesis.text(), "Executable AST already researched."))
            return
        self.status("synthetic_checks", directory)
        check = directory / "preflight.json"
        if not check.exists():
            with check.open("w") as stdout, (directory / "preflight.stderr").open("w") as stderr:
                tested = subprocess.run(
                    [sys.executable, "-m", "quant.preflight", str(candidate)],
                    cwd=self.workspace.autoresearch, stdout=stdout, stderr=stderr, timeout=180, check=False)
            if tested.returncode:
                finish(directory, Attempt(str(directory), digest, behavior, "", False, "preflight_failed",
                                          hypothesis.text(), (directory / "preflight.stderr").read_text()[-6000:]))
                return
        if not json.loads(check.read_text()).get("passed"):
            raise FactoryError("Incomplete synthetic check artifact")
        self.status("evaluating", directory)
        if not own_result.exists():
            if evaluation.exists():
                raise FactoryError("Interrupted evaluation needs reconciliation with the study ledger")
            with (directory / "evaluate.stdout").open("w") as stdout, (directory / "evaluate.stderr").open("w") as stderr:
                evaluated = subprocess.run(
                    [sys.executable, str(self.workspace.autoresearch / "quant/prepare.py"),
                     "--candidate", str(candidate), "--hypothesis", hypothesis.text(), "--output", str(evaluation)],
                    stdout=stdout, stderr=stderr, timeout=1500, check=False)
            if evaluated.returncode and not own_result.exists():
                raise FactoryError("Evaluator failed before recording a terminal outcome")
        outcome = json.loads(own_result.read_text())
        if outcome["status"] == "crash":
            finish(directory, Attempt(str(directory), digest, behavior, "", False, "crash",
                                      hypothesis.text(), (evaluation / "attempt.json").read_text()))
            return
        if outcome["source_sha256"] != digest:
            raise FactoryError("Numeric result does not match the preregistered candidate")
        pnl = source_hash(study / "runs" / outcome["run_id"] / "pnl.csv")
        earlier_pnl = {source_hash(path) for path in (study / "runs").glob("*/pnl.csv")
                       if path.parent.name != outcome["run_id"]}
        self.status("native_harness_review", directory)
        task = (
            "Interpret this ONE completed hypothesis with the supplied fixed evidence. "
            "Its scripts/train.py is frozen for this entire task: do not change it or run "
            "another strategy. Improve only research instructions and skill application. "
            "Read the three scientific skills and Quant references. Report every failure "
            "and rival explanation; suggest one falsifiable next question. No subagents.\n" + hypothesis.text())
        adapter = QuantAdapter(QuantWorkspace(directory / "harness", self.workspace.autoresearch,
                                              self.workspace.scientific_skills, candidate, evaluation), task)
        adapter.spec = replace(adapter.spec, prompts=replace(adapter.spec.prompts,
                               dom_levers="domain-specific research interpretation instructions"))
        library = Library(self.workspace.output / "library/seq", "daily-equities", adapter.substrate.surface())
        proposer = Proposer(adapter.spec.channels["proposer"], audit_dir=directory / "model-audit", attempts=1)
        result = run_task("hypothesis-" + directory.name, 1, adapter=adapter, prop=proposer,
                          runs_root=adapter.spec.runs_root, modes=("seq",), libraries={"seq": library})
        if result.status not in {"ok", "skipped"} or result.errors:
            raise FactoryError(f"Native Harness² task failed: {result.status} {result.errors}")
        if result.modes["seq"].get("fell_back"):
            raise FactoryError("Native proposal fell back; inspect its audit before advancing")
        selected = Path(result.selections["seq"]["chosen_run_dir"])
        note = adapter.deliverable_text(selected)
        duplicate = pnl in earlier_pnl
        finish(directory, Attempt(str(directory), digest, behavior, pnl, not duplicate,
                                  "duplicate_pnl" if duplicate else outcome["status"], hypothesis.text(), note))
        self.status("hypothesis_completed", directory)
