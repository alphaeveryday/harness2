"""Factory counters must represent completed new work, never replays or crashes."""
import fcntl
import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from harness2.benchmarks.quant import QuantWorkspace
from harness2.benchmarks.quant_factory import Factory
from harness2.benchmarks.quant_factory_state import (
    Attempt,
    FactoryError,
    behavior_hash,
    finish,
    history,
)
from harness2.core import recursion, schedule
from harness2.demo import DemoAdapter, DemoProposer


class FactoryTests(unittest.TestCase):
    def test_comments_and_docstrings_do_not_create_new_alpha(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "alpha.py"
            path.write_text('"""idea one"""\ndef alpha(d):\n    return d.returns\n')
            first = behavior_hash(path)
            path.write_text('"""renamed idea"""\n# cosmetic change\ndef alpha(d):\n    return d.returns\n')
            self.assertEqual(first, behavior_hash(path))
            path.write_text('def alpha(d):\n    return -d.returns\n')
            self.assertNotEqual(first, behavior_hash(path))

    def test_failed_and_duplicate_records_do_not_fill_quota_and_resume_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = QuantWorkspace(root, root, root)
            for index, (status, counted) in enumerate((("crash", False), ("duplicate", False), ("discard", True))):
                directory = root / "attempts" / str(index)
                directory.mkdir(parents=True)
                attempt = Attempt(str(directory), "hash", "ast", "pnl", counted, status, "idea", "note")
                finish(directory, attempt)
                finish(directory, attempt)
            factory = Factory(workspace, 1, root / "history.md")
            study = root / "study"
            study.mkdir()
            with patch.dict(os.environ, {"QUANTLAB_HOME": str(study), "QUANTLAB_REPO": str(root)}), \
                 patch.object(Factory, "_freeze_inputs"), patch.object(Factory, "_one") as execute:
                factory.run()
            execute.assert_not_called()
            self.assertEqual(sum(a.counted for a in history(root)), 1)
            self.assertEqual(json.loads((root / "status.json").read_text())["phase"], "completed")

    def test_two_factories_cannot_share_a_study(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            study = root / "study"
            locks = study / ".local/autoresearch"
            locks.mkdir(parents=True)
            factory = Factory(QuantWorkspace(root, root, root), 1, root / "history.md")
            with (locks / "factory.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.dict(os.environ, {"QUANTLAB_HOME": str(study)}), self.assertRaises(FactoryError):
                    factory.run()

    def test_serial_spec_reaches_original_recursion_and_original_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            adapter = DemoAdapter(Path(temporary))
            adapter.spec = replace(adapter.spec, serial_execution=True)
            proposer = DemoProposer(adapter.spec.channels["proposer"])
            with patch("harness2.core.schedule.recursion.run_mode", wraps=recursion.run_mode) as native:
                result = schedule.run_task(adapter.tasks()[0], 1, adapter=adapter, prop=proposer,
                                           runs_root=adapter.spec.runs_root, modes=("seq",))
                self.assertEqual(result.status, "ok")
                self.assertEqual(native.call_args.kwargs["propose_workers"], 1)
                self.assertEqual(native.call_args.kwargs["rollout_workers"], 1)
                before = adapter.execution_count
                again = schedule.run_task(adapter.tasks()[0], 1, adapter=adapter, prop=proposer,
                                          runs_root=adapter.spec.runs_root, modes=("seq",))
                self.assertEqual(again.status, "skipped")
                self.assertEqual(adapter.execution_count, before)


if __name__ == "__main__":
    unittest.main()
