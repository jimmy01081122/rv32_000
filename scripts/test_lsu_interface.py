#!/usr/bin/env python3
"""Qualification must not leave an old green summary after a compiler failure."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InterfaceEvidenceGuard(unittest.TestCase):
    def test_compiler_failure_removes_old_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / 'report'
            out.mkdir()
            summary = out / 'summary.json'
            summary.write_text(json.dumps({'passed': True, 'stale': True}))
            sim = base / 'fake-sim'
            sim.write_text('#!/bin/sh\nprintf "PASS (0)\\nDMEM ENV blocked_load_cycles=1\\n"\n')
            compiler = base / 'riscv-none-elf-gcc'
            compiler.write_text('#!/bin/sh\nprintf "forced compiler failure\\n"\nexit 42\n')
            for path in (sim, compiler):
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(base))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_lsu_interface.py'),
                                     '--sim', str(sim), '--out', str(out)],
                                    cwd=ROOT, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('forced compiler failure', result.stdout)
            self.assertFalse(summary.exists(), 'stale PASS survived aborted qualification')


if __name__ == '__main__':
    unittest.main()
