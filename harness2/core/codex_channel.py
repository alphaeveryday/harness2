"""Local Codex transport; retain Proposer's upstream cache, harvest and audit."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
from pathlib import Path


def run_codex(cwd: Path, prompt: str, timeout: int) -> tuple[str, float, str]:
    """Use the operator's configured model and credentials without disabling sandboxing."""
    answer = cwd / "codex-answer.md"
    argv = [
        shutil.which("codex") or "codex", "exec", "--sandbox", "workspace-write",
        "--skip-git-repo-check", "--ephemeral", "--color", "never",
        "--output-last-message", str(answer), "-",
    ]
    with (cwd / "codex-stdout.log").open("w") as stdout, (
        cwd / "codex-stderr.log"
    ).open("w") as stderr:
        with subprocess.Popen(argv, cwd=cwd, text=True, stdin=subprocess.PIPE,
                              stdout=stdout, stderr=stderr, start_new_session=True) as process:
            try:
                process.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                return "", 0.0, f"Codex exceeded {timeout} seconds; its process group was stopped"
    if process.returncode != 0:
        return "", 0.0, f"Codex exited with status {process.returncode}"
    if not answer.is_file():
        return "", 0.0, "Codex produced no final message"
    # Codex CLI does not supply a billed USD value here; zero is not a free-call claim.
    return answer.read_text(encoding="utf-8"), 0.0, ""
