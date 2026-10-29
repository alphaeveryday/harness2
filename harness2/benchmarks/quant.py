"""Quant adapter using upstream recursion and the actual autoresearch fork."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..core import tree
from ..core.codex_channel import run_codex
from ..core.spec import BenchPrompts, BenchSpec, ChannelSpec
from ..substrate.codex import CodexSubstrate

SKILLS: Final = ("hypothesis-generation", "scientific-critical-thinking", "statistical-analysis")


class QuantContractError(ValueError):
    """A candidate does not retain the Quant experiment boundary."""


@dataclass(frozen=True, slots=True)
class QuantWorkspace:
    output: Path
    autoresearch: Path
    scientific_skills: Path


class QuantAdapter:
    """Own a serial development evaluator and its materialized research context."""

    def __init__(self, workspace: QuantWorkspace, task: str):
        self.workspace = workspace
        self.task = task
        self.substrate = CodexSubstrate()
        self._lock = threading.Lock()
        self.execution_count = 0
        channel = ChannelSpec("codex_cli", "operator-configured", timeout=900)
        self.spec = BenchSpec(
            name="quant", runs_root=workspace.output / "runs", install_mode="codex_root",
            prompts=BenchPrompts(
                work="investigate predictive daily-equity models with a fixed research protocol",
                inv_levers="research instructions and scientific skill use",
                dom_levers="the causal candidate implementation in scripts/train.py",
                yardstick="traceable research artifacts, explicit limitations and reproducibility",
            ),
            channels={"proposer": channel, "selector": channel},
            reserved_scripts=frozenset({"prepare.py"}),
            leak_globs=("*holdout*", "*.parquet", "*.env"),
        )
        self._materialize()

    def _materialize(self) -> None:
        profile = self.workspace.autoresearch / "quant"
        base = {"AGENTS.md": (profile / "program.md").read_text(encoding="utf-8"),
                "scripts/train.py": (profile / "train.py").read_text(encoding="utf-8")}
        manifest: dict[str, str] = {}
        for skill in SKILLS:
            source = self.workspace.scientific_skills / "skills" / skill
            for path in sorted(source.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    relative = f".agents/skills/{skill}/{path.relative_to(source).as_posix()}"
                    if tree.is_allowed(self.substrate.surface(), relative):
                        base[relative] = path.read_text(encoding="utf-8")
                        manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        for skill in SKILLS:
            if f".agents/skills/{skill}/SKILL.md" not in base:
                raise QuantContractError(f"Missing required upstream skill: {skill}")
        tree.validate(self.substrate.surface(), base, allow_subagents=False,
                      reserved_scripts=self.spec.reserved_scripts)
        root = self.workspace.output
        root.mkdir(parents=True, exist_ok=True)
        inputs = {"task": self.task, "sources": {key: hashlib.sha256(value.encode()).hexdigest()
                  for key, value in base.items()},
                  "evaluator": hashlib.sha256((profile / "prepare.py").read_bytes()).hexdigest(),
                  "study": {key: os.environ.get(key) for key in
                            ("QUANTLAB_REPO", "QUANTLAB_HOME", "QUANTLAB_PROTOCOL")}}
        frozen = root / "inputs.json"
        if frozen.exists() and json.loads(frozen.read_text()) != inputs:
            raise QuantContractError("Task, profile or study changed; use a new output directory")
        frozen.write_text(json.dumps(inputs, indent=2), encoding="utf-8")
        provenance = root / "skill-sources.json"
        if provenance.exists() and json.loads(provenance.read_text()) != manifest:
            raise QuantContractError("Skill sources changed; use a new output directory")
        provenance.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)
        source = self.task_files("development")
        source.mkdir(parents=True, exist_ok=True)
        (source / "task.txt").write_text(self.task, encoding="utf-8")

    def tasks(self, split: str = "all") -> list[str]:
        return ["development"]

    def domain_of(self, task_id: str) -> str:
        return "daily-equities"

    def task_prompt(self, task_id: str) -> str:
        return self.task

    def task_files(self, task_id: str) -> Path:
        return self.workspace.output / "source"

    def base_harness(self) -> Path:
        return self.workspace.output / "base"

    def validate_tree(self, candidate: tree.Tree) -> None:
        if "scripts/train.py" not in candidate:
            raise QuantContractError("The Quant executor requires scripts/train.py")
        if any(path.startswith("scripts/") and path != "scripts/train.py" for path in candidate):
            raise QuantContractError("The fixed executor runs only scripts/train.py")
        for skill in SKILLS:
            if f".agents/skills/{skill}/SKILL.md" not in candidate:
                raise QuantContractError(f"The research context must retain {skill}")

    def execute(
        self, task_id: str, harness_dir: Path | None, run_id: str, *, timeout: int | None = None
    ) -> Path:
        """Implement the upstream adapter signature; serialize access to the study ledger."""
        relative = Path(run_id)
        if relative.is_absolute() or ".." in relative.parts:
            raise QuantContractError("Run identity must remain within the execution directory")
        directory = self.workspace.output / "executions" / relative
        harness = harness_dir or self.base_harness()
        self.validate_tree(tree.read_tree(self.substrate.surface(), harness))
        candidate = harness / "scripts/train.py"
        with self._lock:
            cached = (directory / "result.json").is_file()
            if cached:
                if (directory / "train.py").read_bytes() != candidate.read_bytes():
                    raise QuantContractError("A completed run identity cannot change its source")
                if self.delivered(directory):
                    return directory
            else:
                directory.parent.mkdir(parents=True, exist_ok=True)
                self.execution_count += 1
                process = subprocess.run(
                    [sys.executable, str(self.workspace.autoresearch / "quant/prepare.py"),
                     "--candidate", str(candidate), "--hypothesis", self.task,
                     "--output", str(directory)],
                    capture_output=True, text=True, timeout=timeout or 1400, check=False,
                )
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "trajectory.md").write_text(
                    "[ACTION] Run the fixed autoresearch Quant evaluator\n[OBSERVATION]\n"
                    + process.stdout + "\n[ERROR]\n" + process.stderr, encoding="utf-8",
                )
                if process.returncode:
                    raise QuantContractError(f"Quant evaluator failed; see {directory / 'trajectory.md'}")
        self._research_report(harness, directory)
        return directory

    def _research_report(self, harness: Path, directory: Path) -> None:
        """Execute the chosen instructions against actual results and retain the model trace."""
        workspace = Path(tempfile.mkdtemp(prefix="researcher-", dir=directory))
        tree.write_tree(self.substrate.surface(), tree.read_tree(self.substrate.surface(), harness),
                        workspace, stubs=False)
        evidence = workspace / "evidence"
        evidence.mkdir()
        for name in ("result.json", "assessment.json", "hypothesis.txt"):
            shutil.copyfile(directory / name, evidence / name)
        original = (workspace / "scripts/train.py").read_bytes()
        prompt = (
            "Complete one bounded research-report task, then stop. Read AGENTS.md, the three "
            "installed scientific SKILL.md files and their references/quant-development.md. "
            "The fixed evaluator has ALREADY run; its actual artifacts are in evidence/. "
            "Do not run another experiment, change scripts/train.py, read outside this "
            "workspace, access raw market data, call external services, or place orders. "
            "Use the selected harness instructions to interpret these artifacts. Return "
            "a concise research note (at most 250 words) stating observation, fixed "
            "comparison, interpretation limits and one falsifiable next question. Cite "
            "artifact filenames and fields. A failed development screen remains failed. "
            "No additional tests, installations or diagrams are needed for this report.\n\n"
            + self.task
        )
        note, _, error = run_codex(workspace, prompt, 900)
        if error or not note.strip():
            raise QuantContractError(f"Researcher failed: {error}; trace in {workspace}")
        if original != (workspace / "scripts/train.py").read_bytes():
            raise QuantContractError("Reporting researcher changed the already evaluated candidate")
        (directory / "research_note.md").write_text(note, encoding="utf-8")
        with (directory / "trajectory.md").open("a", encoding="utf-8") as trajectory:
            trajectory.write("\n[ACTION] Codex researcher reads the installed harness and results\n"
                             "[OBSERVATION]\n" + note + "\n")

    def delivered(self, run_dir: Path) -> bool:
        return all((run_dir / name).is_file() for name in
                   ("result.json", "assessment.json", "research_note.md"))

    def trajectory(self, run_dir: Path, *, obs_trunc: int) -> str:
        return (run_dir / "trajectory.md").read_text(encoding="utf-8")

    def deliverable_text(self, run_dir: Path) -> str:
        return (run_dir / "research_note.md").read_text(encoding="utf-8")

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        return {name: (run_dir / name).read_text(encoding="utf-8")
                for name in ("research_note.md", "result.json", "assessment.json", "hypothesis.txt")}
