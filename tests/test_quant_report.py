"""A numeric replay is incomplete until the selected harness authors a report."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness2.benchmarks.quant import SKILLS, QuantAdapter, QuantContractError, QuantWorkspace


class QuantReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        profile = root / "autoresearch/quant"
        profile.mkdir(parents=True)
        (profile / "program.md").write_text("Use " + ", ".join(SKILLS))
        (profile / "train.py").write_text("def alpha(d):\n    return 1\n")
        (profile / "prepare.py").write_text("pass\n")
        for name in SKILLS:
            skill = root / "science/skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")
        self.adapter = QuantAdapter(QuantWorkspace(root / "output", profile.parent, root / "science"), "task")
        self.run = root / "run"
        self.run.mkdir()
        for name in ("result.json", "assessment.json", "hypothesis.txt"):
            (self.run / name).write_text('{}')
        (self.run / "trajectory.md").write_text("[ACTION] fixed evaluator\n")

    def test_numeric_artifacts_alone_do_not_complete_the_task(self):
        # Given numeric artifacts; when delivery is checked; then reject the missing report.
        self.assertFalse(self.adapter.delivered(self.run))

    def test_selected_harness_runs_a_researcher_before_delivery(self):
        # Given a completed evaluator and an external researcher boundary.
        with patch("harness2.benchmarks.quant.run_codex", return_value=("authored result", 0.0, "")) as model:
            # When the real report orchestration materializes and calls that researcher.
            self.adapter._research_report(self.adapter.base_harness(), self.run)
        # Then the authored artifact and selected skills accompany the actual result.
        workspace = model.call_args.args[0]
        self.assertEqual((workspace / "evidence/result.json").read_bytes(), (self.run / "result.json").read_bytes())
        self.assertTrue((workspace / ".agents/skills/statistical-analysis/SKILL.md").is_file())
        self.assertEqual((self.run / "research_note.md").read_text(), "authored result")
        self.assertTrue(self.adapter.delivered(self.run))

    def test_reporter_cannot_change_the_already_evaluated_candidate(self):
        def changing_reporter(workspace: Path, prompt: str, timeout: int):
            (workspace / "scripts/train.py").write_text("def alpha(d):\n    return 2\n")
            return "partial report", 0.0, ""

        # Given a researcher that changes the frozen candidate.
        with patch("harness2.benchmarks.quant.run_codex", side_effect=changing_reporter):
            # When it reports, then its artifact is not accepted as complete.
            with self.assertRaises(QuantContractError):
                self.adapter._research_report(self.adapter.base_harness(), self.run)
        self.assertFalse(self.adapter.delivered(self.run))


if __name__ == "__main__":
    unittest.main()
