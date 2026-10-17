#!/usr/bin/env python3
"""Reject unfair or incomplete contraction comparisons."""
import copy
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
