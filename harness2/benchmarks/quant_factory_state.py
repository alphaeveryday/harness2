"""Durable accounting for individually researched hypotheses."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


class FactoryError(RuntimeError):
    """The supervisor cannot safely advance its current hypothesis."""


class FactoryBusy(FactoryError):
    """Another live supervisor owns the study; its status must remain untouched."""


@dataclass(frozen=True, slots=True)
class Hypothesis:
    mechanism: str
    parent: str
    change: str
    rival: str
    falsifier: str
    informed_by: str

    @classmethod
    def read(cls, path: Path) -> Hypothesis:
        raw = json.loads(path.read_text())
        fields = ("mechanism", "parent", "change", "rival", "falsifier", "informed_by")
        values = [raw[key] for key in fields]
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise FactoryError("Every hypothesis field must contain a nonempty string")
        return cls(*values)

    def text(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass(frozen=True, slots=True)
class Attempt:
    directory: str
    source_hash: str
    behavior_hash: str
    pnl_hash: str
    counted: bool
    status: str
    hypothesis: str
    note: str

    @classmethod
    def read(cls, path: Path) -> Attempt:
        return cls(**json.loads(path.read_text()))


def atomic_json(path: Path, payload: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def behavior_hash(path: Path) -> str:
    """Ignore comments, docstrings and formatting when detecting repeated code."""
    module = ast.parse(path.read_text())
    for node in ast.walk(module):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body.pop(0)
    return hashlib.sha256(ast.dump(module, include_attributes=False).encode()).hexdigest()


def history(root: Path) -> list[Attempt]:
    return [Attempt.read(path) for path in sorted((root / "attempts").glob("*/complete.json"))]


def finish(directory: Path, attempt: Attempt) -> None:
    target = directory / "complete.json"
    if target.exists():
        if Attempt.read(target) != attempt:
            raise FactoryError("An attempt's terminal evidence cannot be overwritten")
        return
    atomic_json(target, json.dumps(asdict(attempt), ensure_ascii=False, indent=2))


def context_text(attempts: list[Attempt]) -> str:
    """Carry all hypothesis decisions plus recent detailed reports, without a quota."""
    compact = [
        {"hypothesis": item.hypothesis, "status": item.status, "source": item.source_hash,
         "counted": item.counted} for item in attempts
    ]
    recent = "\n\n".join(item.note for item in attempts[-5:])
    return json.dumps(compact, ensure_ascii=False, indent=2) + "\nRecent reports:\n" + recent
