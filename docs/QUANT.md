# Quant Lab profile

## Current entrypoint: one serial alpha factory

The old replay CLI described below is retired. Its `--task-file`, `--k`, `--mode`
and `--prepare-only` controls no longer exist. The historical description below
documents the initial integration evidence, not another active research agent.

```bash
export QUANTLAB_REPO=/path/to/locked/quant-lab-research
export QUANTLAB_HOME=/path/to/inherited/study
export QUANTLAB_PROTOCOL=/path/to/frozen/PROTOCOL.md
cd /path/to/harness2
/path/to/locked/python -m harness2.cli.quant \
  --autoresearch /path/to/autoresearch \
  --scientific-skills /path/to/scientific-agent-skills \
  --output /path/to/factory-run \
  --history-file /path/to/inherited-research.md --minimum-attempts 100
```

One fresh author sees one hypothesis task, inherited failures and recent native
Harness² experience. The author never receives the supervisor's target count.
It writes a hypothesis and one candidate before seeing numeric results. Trusted
`quant/preflight.py` checks synthetic prefixes, future perturbations, repeated
calls and output alignment. The fixed `prepare.py` runs the candidate once.
The inherited Quant Lab audited runner and assessor remain deterministic
numeric dependencies, not a second agent loop.

The supervisor then calls the original `core.schedule.run_task` with k=1 and
only sequential mode. Proposal and rollout widths are both one. The candidate
is frozen throughout that task: INV/DOM/COMPOSE improve research instructions,
and four actual reports share the same numerical evidence. The original
reflection/library and selected report feed the following hypothesis. No new
candidate is authored until the preceding review finishes.

`status.json` records progress. `attempts/*/complete.json` records terminal
decisions; each attempt retains hypothesis, sealed source, preflight results,
numeric evidence and native Harness² artifacts. The minimum counts completed
new candidates with distinct executable AST and PnL. Comments, replays,
duplicates and crashes do not fill the quota. This is not a count of independent
statistical hypotheses. The prior study and all its failures remain intact.

A study-wide flock excludes duplicate supervisors. Completed attempts resume
without model calls or simulation. Interrupted unsealed authors and incomplete
evaluations stop for reconciliation, rather than silently duplicating work.
Two consecutive invalid or duplicate attempts stop with evidence. A `STOP` file
in the output root stops between hypotheses. `--status` prints the checkpoint.
Optional `QUANT_FACTORY_CHANNEL`, `QUANT_FACTORY_REPLY`, `QUANT_FACTORY_OWNER`
publish authorized milestones to the originating Buzz thread. Final holdout,
submission and orders remain disabled; promotion remains false.

## Historical replay integration (retired CLI)

This fork executes the original `core.schedule.run_domain`, Propose–Probe–Compose,
selection, reflection, and library implementation against a Quant adapter. It
does not replace the upstream method with a separate experiment loop.

The three checked-out forks are:

- `alphaeveryday/harness2`, upstream `1cfe254e8d25b15f37048c3730134686abe60335`.
- `alphaeveryday/autoresearch`, upstream `228791fb499afffb54b46200aca536f79142f117`.
- `alphaeveryday/scientific-agent-skills`, upstream `5f2bc0341354fd5590aef76a533ada1e1e5b4e62`.

Use their `feature/quant-lab` branches. All original histories and licenses are
preserved. The scientific skills retain their original procedures and resources,
with a versioned Quant-specific addition to hypothesis-generation,
scientific-critical-thinking and statistical-analysis. This integration cites
their actual fork files; the upstream collection also provides its paper citation
in `CITATION.cff`.

## Run

Use a Quant Lab checkout containing the existing audited
`scripts/autoresearch.py`, `scripts/assess_candidate.py` and their dependencies.
That research checkout must retain the fixed engine, settings and dataset needed
by its assessment policy. Run this module with its locked Python interpreter;
Harness² itself adds no Python dependency for this profile.

```bash
export QUANTLAB_REPO=/path/to/locked/quant-lab-research
export QUANTLAB_HOME=/path/to/persistent/study
export QUANTLAB_PROTOCOL=/path/to/frozen/PROTOCOL.md
# Copy the prior study's complete runs/ into a new study once, if needed.
# Do not initialize a blank ledger or copy only successful runs.

cd /path/to/harness2
/path/to/quant-lab/.venv/bin/python -m harness2.cli.quant \
  --autoresearch /path/to/autoresearch \
  --scientific-skills /path/to/scientific-agent-skills \
  --output /path/to/new-harness-run \
  --task-file /path/to/research-task.txt --k 1 --mode sequential
```

`--output` must be outside `QUANTLAB_HOME`. `--prepare-only` materializes and
validates the context without model calls or market-data evaluation. The actual
command invokes the operator's configured `codex exec` with a workspace-write
sandbox. It does not provision credentials, choose a new model, or disable
approval/sandbox protections. The CLI does not provide billed USD here; an audit
value of zero is not evidence that calls are free.

The adapter copies `quant/program.md` into the base `AGENTS.md`, `quant/train.py`
into `scripts/train.py`, and all supported text resources of the three original
scientific skills into `.agents/skills/`. Their hashes are in `skill-sources.json`.
The immutable `quant/prepare.py` remains outside the editable harness. Each probe
calls it, which invokes the existing Quant Lab runner and assessor. Actual qlab
evaluations are serialized even when the upstream method proposes in parallel.

After each evaluation, an actual Codex researcher consumes the selected harness,
the three installed skills and the fixed numeric artifacts to produce
`research_note.md`. It cannot change the already evaluated candidate. This authored
interpretation and the retained local model transcript enter the upstream
Propose–Probe–Compose evidence. Numeric replay alone is not a delivered task.

The first integration task replays frozen M1 and edits research guidance only.
It is not a new candidate search or investment-performance validation. A normal
authorized research task can propose changes to `scripts/train.py` while keeping
its settings fixed; causal tests remain required by the research program.

## Evidence and resume

Inspect `quant.json`, `runs/*/development/summary.json`, `model-audit/`,
`executions/`, `library/`, and the Quant study's immutable run registry and
`results.tsv`. An unchanged output can resume without new executions. Changing
the task, source profile, skills or study requires a new output directory, while
retaining the study history. A reported failed base/probe is not a completed
research result. The upstream method can fall back from a failed proposal; inspect
the `fell_back`/error fields before claiming every stage succeeded.

Harness adoption selects a working research harness. Autoresearch `keep` means
the fixed development screen passed. Neither is investment approval. The known
Quant engine future-bar dependency is unresolved, so every profile outcome has
`promotion_eligible=false`; final holdout, submit, deployment and orders are not
part of this adapter. Settings checks and output hashes are integrity checks,
not a security sandbox for arbitrary hostile Python candidates.

## Verification

Run the full Harness² suite with `python -m unittest discover -s tests -v`.
The added tests cover skill resource retention, relative helper paths, traversal
rejection and the real Codex transport/harvest boundary. The autoresearch fork's
full `tests/` suite covers fixed trading settings and output separation. The
scientific fork uses its own repo-wide structural checks and isolated per-skill
suites. Report local-model and market-data runs separately from deterministic
transport fixtures.
