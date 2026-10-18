#!/usr/bin/env python3
"""Reject incomplete cycle attribution and inconsistent ROI observations."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import profile_fp_bottlenecks as driver


class ProfileContract(unittest.TestCase):
    def setUp(self):
        self.profile = {'cycles': 8, 'trace_mismatches': 0, 'layout_mismatches': 0,
                        'cycle_partition': {'retired_body': 3, 'retired_marker': 1,
                                            'store_ack_wait': 2, 'head_wait_fp_load': 2},
                        'retired_classes': {'fma': 3}, 'store_ack_wait_phases': {'mark_pending': 2},
                        'load_head_wait_phases': {'own_external_inflight': 2}}
        self.numeric = {'passed': True, 'roi_cycles': 8, 'checksum': 'abcd'}
        self.record = {'dut_numeric': self.numeric}

    def problems(self, profile):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'dut.txt'
            log.write_text('FP ROI cycle_reads=2 retired=3 fmadd_s=3\n')
            with patch.object(driver, 'validate', return_value=self.numeric):
                return driver.check_profile(profile, self.record, {}, log)[1]

    def test_complete_profile(self):
        self.assertEqual(self.problems(self.profile), [])

    def test_dropped_partition_cycle(self):
        p = copy.deepcopy(self.profile); p['cycle_partition']['store_ack_wait'] = 1
        self.assertIn('cycle partition is incomplete', self.problems(p))

    def test_wrong_roi_boundary(self):
        p = copy.deepcopy(self.profile); p['cycles'] = 9
        self.assertIn('CSR ROI cycles / observed commit-window cycles disagree', self.problems(p))

    def test_layout_or_trace_mismatch(self):
        for field in ('layout_mismatches', 'trace_mismatches'):
            p = copy.deepcopy(self.profile); p[field] = 1
            self.assertIn('pre-edge decode / commit or packed-layout consistency failed', self.problems(p))

    def test_missing_store_phase(self):
        p = copy.deepcopy(self.profile); p['store_ack_wait_phases'] = {}
        self.assertIn('store wait phases are incomplete', self.problems(p))


if __name__ == '__main__':
    unittest.main()
