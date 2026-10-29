"""One fresh research workspace authors one hypothesis, without a batch target."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..core.codex_channel import run_codex
from .quant import QuantAdapter, QuantWorkspace
from .quant_factory_state import (
    Attempt,
    FactoryError,
    Hypothesis,
    atomic_json,
    context_text,
    source_hash,
)


def author(
    directory: Path, workspace: QuantWorkspace, engine: Path, attempts: list[Attempt],
    inherited: str,
) -> tuple[Path, Hypothesis]:
    """Seal source and hypothesis before the supervisor can read market results."""
    sealed = directory / "sealed.json"
    candidate = directory / "train.py"
    hypothesis_path = directory / "hypothesis.json"
    if sealed.exists():
        saved = json.loads(sealed.read_text())
        actual = {"source": source_hash(candidate), "hypothesis": source_hash(hypothesis_path)}
        if saved != actual:
            raise FactoryError("The preregistered candidate or hypothesis changed")
        return candidate, Hypothesis.read(hypothesis_path)
    root = directory / "author"
    if root.exists():
        raise FactoryError("Interrupted unsealed author workspace requires inspection before retry")
    context = QuantAdapter(QuantWorkspace(root, workspace.autoresearch, workspace.scientific_skills),
                           "Prepare one causal hypothesis.")
    agent = context.base_harness()
    evidence = agent / "context"
    evidence.mkdir()
    (evidence / "history.md").write_text(inherited + "\n" + context_text(attempts))
    experience = sorted((workspace.output / "library").rglob("EXPERIENCE.md"))
    (evidence / "harness-experience.md").write_text(
        "\n\n".join(path.read_text() for path in experience[-5:]) or "No adopted experience yet."
    )
    shutil.copyfile(engine / "quantlab/alpha/ops.py", evidence / "ops_reference.py")
    shutil.copyfile(engine / "quantlab/data/panel.py", evidence / "panel_reference.py")
    parents = evidence / "parents"
    parents.mkdir()
    for path in sorted((engine / "alphas").glob("*.py")):
        shutil.copyfile(path, parents / path.name)
    for item in attempts:
        path = Path(item.directory) / "train.py"
        if path.is_file():
            shutil.copyfile(path, parents / (Path(item.directory).name + ".py"))
    prompt = (
        "Research exactly ONE next daily-equity alpha hypothesis, then stop. You are alone "
        "in this isolated candidate workspace; other sessions may exist elsewhere, so never "
        "change anything outside it. Read AGENTS.md and the three installed scientific "
        "SKILL.md files with references/quant-development.md. Read context/history.md, "
        "context/harness-experience.md and "
        "relevant parent sources. Choose one mechanism informed by failures and rival "
        "explanations. Do not create a list of ideas, a parameter grid, multiple strategies, "
        "or launch any other agent. Prefer a falsifiable new mechanism over cosmetic or "
        "tiny parameter changes. ML is allowed, not mandatory.\n"
        "FIRST write hypothesis.json with nonempty string fields mechanism, parent, change, "
        "rival, falsifier, informed_by. Parent must name an available source; change must "
        "describe one controlled change or one coherent mechanism. THEN implement it in "
        "scripts/train.py. Preserve the exact SETTINGS mapping. Use only d and imports "
        "from quantlab.alpha.ops; the existing API exposes np and pd. No external packages, "
        "files, network, private d attributes, orders, raw market data or hidden periods. "
        "Return a DataFrame aligned to d.dates and d.codes. Forward labels must mature by "
        "the signal date: delay-1 earns s+2. Handle NaNs, late listings and zero volume. "
        "The supervisor alone will run trusted synthetic checks and the fixed evaluator. "
        "Do not run simulations or change checks. Write only hypothesis.json and "
        "scripts/train.py. Finish with the causal mechanism and expected falsifying observation."
    )
    (root / "prompt.txt").write_text(prompt)
    answer, _, error = run_codex(agent, prompt, 1200)
    if error or not answer.strip():
        raise FactoryError(f"Author failed: {error}; inspect {agent}")
    hypothesis = Hypothesis.read(agent / "hypothesis.json")
    shutil.copyfile(agent / "scripts/train.py", candidate)
    hypothesis_path.write_text(hypothesis.text())
    atomic_json(sealed, json.dumps({"source": source_hash(candidate),
                                   "hypothesis": source_hash(hypothesis_path)}))
    return candidate, hypothesis
