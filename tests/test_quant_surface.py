"""Regressions for complete upstream skills and the local model transport."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness2.benchmarks.quant import SKILLS, QuantAdapter, QuantContractError, QuantWorkspace
from harness2.core import tree
from harness2.core.codex_channel import run_codex
from harness2.core.proposer import Proposer
from harness2.core.spec import ChannelSpec
from harness2.substrate.codex import CODEX_SURFACE


class QuantSurfaceTests(unittest.TestCase):
    def test_changed_profile_cannot_reuse_completed_output_namespace(self):
        # Given a materialized profile and its complete required skill set.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "autoresearch/quant"
            profile.mkdir(parents=True)
            (profile / "program.md").write_text("Use " + ", ".join(SKILLS))
            (profile / "train.py").write_text("def alpha(d):\n    return 1\n")
            (profile / "prepare.py").write_text("pass\n")
            for name in SKILLS:
                skill = root / "science/skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: local test\n---\n")
            workspace = QuantWorkspace(root / "output", profile.parent, root / "science")
            QuantAdapter(workspace, "task")
            # When a different candidate attempts to reuse the existing namespace.
            (profile / "train.py").write_text("def alpha(d):\n    return 2\n")
            # Then cached results cannot silently masquerade as the new profile.
            with self.assertRaises(QuantContractError):
                QuantAdapter(workspace, "task")

    def test_skill_resources_survive_materialization_and_library_reads(self):
        # Given a skill with a real relative script and supporting data.
        content = {"AGENTS.md": "Use sample when investigating data.",
                   ".agents/skills/sample/SKILL.md":
                       "---\nname: sample\ndescription: investigate data\n---\n"
                       "python scripts/check.py\n[Reference](references/time.md)",
                   ".agents/skills/sample/scripts/check.py": "print(1)\n",
                   ".agents/skills/sample/references/time.md": "Trading-time convention",
                   ".agents/skills/sample/assets/example.json": '{"days":2}'}
        with tempfile.TemporaryDirectory() as directory:
            # When the real surface validates, writes and reloads the skill.
            tree.validate(CODEX_SURFACE, content)
            tree.write_tree(CODEX_SURFACE, content, Path(directory))
            loaded = tree.read_tree(CODEX_SURFACE, Path(directory))
        # Then all semantic resources remain available, not only SKILL.md.
        self.assertEqual(loaded, content)

    def test_resource_cannot_escape_skill_surface(self):
        # Given a path escaping the skill; when accepted-path logic runs.
        accepted = tree.is_allowed(CODEX_SURFACE, ".agents/skills/sample/references/../../secret.md")
        # Then the resource is rejected.
        self.assertFalse(accepted)

    def test_codex_transport_reads_final_artifact(self):
        # Given an executable boundary with the Codex final-artifact convention.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / "codex"
            cli.write_text('#!/bin/sh\nwhile [ "$1" != "--output-last-message" ]; do shift; done\n'
                           'shift\nprintf "transport delivered" > "$1"\n')
            cli.chmod(0o755)
            with patch("harness2.core.codex_channel.shutil.which", return_value=str(cli)):
                # When the real subprocess transport runs.
                answer, _, error = run_codex(root, "input", 5)
        # Then it returns the actual artifact without a model-service assumption.
        self.assertEqual((answer, error), ("transport delivered", ""))

    def test_codex_transport_rejects_failed_process_with_partial_artifact(self):
        # Given a process that writes an answer but exits unsuccessfully.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / "codex"
            cli.write_text('#!/bin/sh\nwhile [ "$1" != "--output-last-message" ]; do shift; done\n'
                           'shift\nprintf "partial" > "$1"\nexit 17\n')
            cli.chmod(0o755)
            with patch("harness2.core.codex_channel.shutil.which", return_value=str(cli)):
                # When the transport runs, then the partial artifact is not a successful reply.
                answer, _, error = run_codex(root, "input", 5)
            self.assertEqual(answer, "")
            self.assertIn("17", error)

    def test_codex_dispatch_harvests_workspace_and_keeps_audit(self):
        # Given the real proposer with only the external CLI boundary replaced.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source/harness"
            source.mkdir(parents=True)
            (source / "AGENTS.md").write_text("Keep source history")
            proposer = Proposer(ChannelSpec("codex_cli", "operator-configured"), audit_dir=root / "audit")
            with patch("harness2.core.codex_channel.run_codex", return_value=("done", 0.0, "")):
                # When the native cache/harvest path performs the call.
                reply = proposer.call("edit", source.parent, "inv1", harvest="context/harness")
            # Then the harvested input and the durable audit both exist.
            self.assertEqual((reply.workspace / "AGENTS.md").read_text(), "Keep source history")
            self.assertTrue(reply.audit.is_file())
            self.assertEqual(reply.channel, "codex_cli")


if __name__ == "__main__":
    unittest.main()
