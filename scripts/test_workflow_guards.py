#!/usr/bin/env python3
"""Check that absent/stale ACT4 inputs cannot produce a passing regression."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_act4 as act4


class Act4GenerationGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.framework = self.root / 'framework'
        self.framework.mkdir()
        (self.framework / 'Makefile').touch()
        self.elf_dir = self.framework / 'work/rv32_ooo/elfs/rv32i'
        self.report = self.root / 'report'
        self.config = self.root / 'config'
        self.config.mkdir()
        self.tools = {'sail_riscv_sim': '/tools/sail', 'mise': '/tools/mise'}
        for name, value in {
            'ACT4_ROOT': str(self.framework),
            'SRC_CONFIG_DIR': str(self.config),
            'REPORT_DIR': str(self.report),
            'GENERATION_LOG_PATH': str(self.report / 'generation.log'),
            'ELF_DIR': str(self.elf_dir),
        }.items():
            mock = patch.object(act4, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        for target, kwargs in [
            ('shutil.which', {'side_effect': self.tools.get}),
            ('subprocess.check_output', {'return_value': act4.PINNED_ACT_COMMIT}),
        ]:
            mock = patch('run_act4.' + target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)

    def generate(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return act4.ensure_act4_elfs(str(self.report))

    def test_missing_framework_fails(self):
        (self.framework / 'Makefile').unlink()
        with self.assertRaisesRegex(RuntimeError, 'framework missing'):
            self.generate()

    def test_wrong_revision_fails(self):
        with patch('run_act4.subprocess.check_output', return_value='wrong-sha'):
            with self.assertRaisesRegex(RuntimeError, 'differs from pinned'):
                self.generate()

    def test_stale_elf_cannot_replace_missing_reference(self):
        self.elf_dir.mkdir(parents=True)
        stale = self.elf_dir / 'stale.elf'
        stale.touch()
        del self.tools['sail_riscv_sim']
        with self.assertRaisesRegex(RuntimeError, 'requires sail_riscv_sim'):
            self.generate()
        self.assertTrue(stale.exists(), 'Preflight must not delete previous output.')

    def test_missing_generator_fails(self):
        del self.tools['mise']
        with self.assertRaisesRegex(RuntimeError, 'requires mise or uv'):
            self.generate()

    def test_generator_failure_fails(self):
        result = subprocess.CompletedProcess([], 1, '', 'generation failed')
        with patch('run_act4.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'framework build failed'):
                self.generate()

    def test_successful_command_with_no_elfs_fails(self):
        result = subprocess.CompletedProcess([], 0, '', '')
        with patch('run_act4.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'generated 0 ELFs'):
                self.generate()

    def test_fresh_generation_accepts_complete_suite(self):
        def generate(cmd, **kwargs):
            self.assertIn(f'CONFIG_FILES={self.config / "test_config.yaml"}', cmd)
            self.elf_dir.mkdir(parents=True)
            for index in range(58):
                (self.elf_dir / f'test{index}.elf').touch()
            return subprocess.CompletedProcess(cmd, 0, 'fresh generation', '')

        with patch('run_act4.subprocess.run', side_effect=generate):
            self.assertEqual(len(self.generate()), 58)
        self.assertFalse((self.framework / 'config').exists())


class DirectedRegressionGuards(unittest.TestCase):
    def test_empty_suite_fails(self):
        runner = Path(__file__).resolve().parent / 'run_all_tests.sh'
        with tempfile.TemporaryDirectory() as temp:
            sim = Path(temp, 'build/sim/rv32_ooo_sim')
            sim.parent.mkdir(parents=True)
            sim.touch()
            result = subprocess.run(['bash', str(runner)], cwd=temp, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No test ELFs found', result.stderr)


if __name__ == '__main__':
    unittest.main()
