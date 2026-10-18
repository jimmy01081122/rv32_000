#!/usr/bin/env python3
"""Reject unfair or incomplete contraction comparisons."""
import copy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import compare_fp_contraction as driver
import unittest
from compare_fp_contraction import compare
from fp_balanced_fixtures import NAMES


def reports():
    common = {'selected': list(NAMES), 'passed_count': 8, 'all_passed': True,
              'run_dut': True, 'profile_roi': True, 'fast_math': False,
              'simulator_sha256': 'same-dut', 'project_source_sha256': {'source': 'same'},
              'source_identity_sha256': 'same-pins', 'compiler_version_sha256': {'gcc': 'same'}}
    result = []
    for mode in ('off', 'fast'):
        report = copy.deepcopy(common)
        report['fp_contract'] = mode
        report['records'] = [{'name': name, 'passed': True, 'fixture_sha256': name,
            'fixture_header_sha256': name, 'dut_numeric': {'roi_cycles': 100},
            'roi_profile': {'retired': 50}, 'target_build': {'command': ['gcc', '-O3', f'-ffp-contract={mode}',
                f'-I/workspace/fma-comparison/{mode}/{name}/', '-o', f'/workspace/fma-comparison/{mode}/{name}/rv32.elf']}}
            for name in NAMES]
        result.append(report)
    return result


class ControlledComparison(unittest.TestCase):
    def test_failed_process_cannot_reuse_old_score(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / 'new-parent'
            out = base / 'fma-comparison'
            out.mkdir(parents=True)
            report = out / 'comparison.json'
            report.write_text(json.dumps({'all_pairs_valid': True,
                'diagnostic_group_geomean': {'fp32_equal_groups': 2.0}}))
            with patch.object(driver, 'BASE', base), patch('sys.argv', ['compare_fp_contraction.py']), \
                    patch.object(driver.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(driver.main(), 1)
            failed = json.loads(report.read_text())
            self.assertFalse(failed['all_pairs_valid'])
            self.assertEqual(failed['results'], [])
            self.assertNotIn('diagnostic_group_geomean', failed)

    def test_matching_pair(self):
        self.assertTrue(compare(*reports())['all_pairs_valid'])

    def test_changed_input(self):
        a, b = reports(); b['records'][0]['fixture_sha256'] = 'changed'
        self.assertFalse(compare(a, b)['all_pairs_valid'])

    def test_changed_hardware(self):
        a, b = reports(); b['simulator_sha256'] = 'changed'
        self.assertFalse(compare(a, b)['all_pairs_valid'])

    def test_failed_case(self):
        a, b = reports(); b['records'][0]['passed'] = False; b['passed_count'] = 7
        self.assertFalse(compare(a, b)['all_pairs_valid'])

    def test_fast_math_is_not_contraction_only(self):
        a, b = reports(); b['fast_math'] = True
        self.assertFalse(compare(a, b)['all_pairs_valid'])

    def test_other_compiler_flag_changed(self):
        a, b = reports(); b['records'][0]['target_build']['command'][1] = '-O2'
        self.assertFalse(compare(a, b)['all_pairs_valid'])


if __name__ == '__main__':
    unittest.main()
