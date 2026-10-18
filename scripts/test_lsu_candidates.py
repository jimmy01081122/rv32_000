#!/usr/bin/env python3
"""Controls for LSU study correctness, denominator and timing interpretation."""
import copy
import unittest

from profile_lsu_candidates import check_observation, summarize


class LsuStudyControls(unittest.TestCase):
    def setUp(self):
        self.profile = {'cycles': 8, 'trace_mismatches': 0, 'layout_mismatches': 0,
                        'cycle_partition': {'retired_body': 3, 'retired_marker': 1,
                                            'store_ack_wait': 2, 'head_wait_int_load': 2},
                        'retired_classes': {'integer_other': 3},
                        'store_ack_wait_phases': {'mark_pending': 2},
                        'load_head_wait_phases': {'own_external_inflight': 2}}
        self.text = ('[Embench] Benchmark executed in cycles: 8\n'
                     'FP ROI cycle_reads=2 retired=3 fmadd_s=0\n'
                     '  Exit status    : PASS (0)\n')

    def test_valid_embench_profile(self):
        self.assertEqual(check_observation(self.profile, self.text, 'embench')['problems'], [])

    def test_extra_marker_is_rejected(self):
        text = self.text.replace('cycle_reads=2', 'cycle_reads=3')
        self.assertIn('expected exactly two low RDCYCLE markers', check_observation(self.profile, text, 'embench')['problems'])

    def test_program_failure_is_rejected(self):
        text = self.text.replace('PASS (0)', 'FAIL')
        self.assertIn('DUT program self-check/exit failed', check_observation(self.profile, text, 'embench')['problems'])

    def test_wrong_csr_window_is_rejected(self):
        text = self.text.replace('cycles: 8', 'cycles: 9')
        self.assertIn('CSR ROI and observed commit-window cycles differ', check_observation(self.profile, text, 'embench')['problems'])

    def records(self):
        result = []
        for name in ('fir', 'bicg'):
            for latency in (1, 2):
                profile = copy.deepcopy(self.profile)
                profile['cycles'] = 100 if latency == 1 else 120
                result.append({'name': name, 'family': 'fp32', 'latency': latency,
                               'passed': True, 'profile': profile})
        return result

    def test_missing_case_is_rejected(self):
        report = summarize(self.records()[:-1], ('fir', 'bicg'), (1, 2))
        self.assertFalse(report['all_passed'])

    def test_changed_instruction_mix_is_rejected(self):
        rows = self.records(); rows[1]['profile']['retired_classes']['integer_other'] += 1
        self.assertFalse(summarize(rows, ('fir', 'bicg'), (1, 2))['all_passed'])

    def test_ratio_is_memory_slowdown(self):
        report = summarize(self.records(), ('fir', 'bicg'), (1, 2))
        self.assertTrue(report['all_passed'])
        self.assertEqual(report['rows'][1]['slowdown_vs_latency1'], 1.2)
        self.assertNotIn('speedup', report['rows'][1])


if __name__ == '__main__':
    unittest.main()
