#!/usr/bin/env python3
"""Clock-binding controls: a common-frequency result must actually close timing."""
import copy
import json
from pathlib import Path
import unittest
from review_cpu_experiment import qualified_period


class OperatingPoints(unittest.TestCase):
    def setUp(self):
        fixture=Path(__file__).resolve().parents[1]/'docs/evidence/2026-10-18/post-lsu-baseline/physical/boundary-9900-10000ps/closure-review.json'
        self.actual=json.loads(fixture.read_text())
        self.faster={'passed':True,'smallest_tested_passing_period_ps':9900,
                     'qualified_periods_ps':[9900,10000]}

    def choose(self,physical,measured,mode='fastest',periods=(9800,9900,10000)):
        return qualified_period(physical,list(periods),measured,10000,100,mode)

    def test_actual_baseline_aliases_one_qualified_point(self):
        for mode in ['fastest','common-clock']:
            self.assertEqual(self.choose(self.actual,10000,mode,periods=(9900,10000)),10000)

    def test_distinct_qualified_points(self):
        self.assertEqual(self.choose(self.faster,9900),9900)
        self.assertEqual(self.choose(self.faster,10000,'common-clock'),10000)
        with self.assertRaises(ValueError):self.choose(self.faster,10000)
        with self.assertRaises(ValueError):self.choose(self.faster,9900,'common-clock')

    def test_functional_common_clock_cannot_override_failed_timing(self):
        slower={'passed':True,'smallest_tested_passing_period_ps':10100,'qualified_periods_ps':[10100]}
        with self.assertRaises(ValueError):self.choose(slower,10000,'common-clock',periods=(10000,10100))
        self.assertEqual(self.choose(slower,10100,periods=(10000,10100)),10100)
        with self.assertRaises(ValueError):self.choose(self.faster,9800)

    def test_no_closure_no_missing_boundary_no_off_grid(self):
        bad=copy.deepcopy(self.faster);bad['passed']=False
        with self.assertRaises(ValueError):self.choose(bad,9900)
        with self.assertRaises(ValueError):self.choose(self.faster,9900,periods=(9900,10000))
        with self.assertRaises(ValueError):self.choose(self.faster,9900,periods=(9800,9850,9900,10000))
        with self.assertRaises(ValueError):self.choose(self.faster,9900,'unreviewed')


if __name__=='__main__':unittest.main()
