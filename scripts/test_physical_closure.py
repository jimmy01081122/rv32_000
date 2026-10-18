#!/usr/bin/env python3
"""Real archived STA failures must never become a qualified CPU clock."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from check_physical_closure import review_corner, worst_slack, check_constraints

EVIDENCE=Path(__file__).resolve().parents[1]/'docs/evidence/2026-10-18/physical-report-validation'


class Closure(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.corner=Path(self.directory.name)/'TT'
        shutil.copytree(EVIDENCE/'TT',self.corner)

    def tearDown(self):self.directory.cleanup()

    def test_all_actual_corners_reject_hold_failures(self):
        for corner in ('TT','SS','FF'):
            result=review_corner(EVIDENCE/corner,corner,[2300,5500])
            self.assertTrue(all(not row['passed'] for row in result['trials']))
            self.assertTrue(all('hold violation' in row['problems'] for row in result['trials']))

    def test_actual_constraint_and_load_failures_block_trial(self):
        shutil.copy2(EVIDENCE/'negative/missing-input-delay.rpt',self.corner/'check_setup_5500.rpt')
        shutil.copy2(EVIDENCE/'negative/excess-load.rpt',self.corner/'electrical_5500.rpt')
        problems=review_corner(self.corner,'TT',[2300,5500])['trials'][1]['problems']
        self.assertIn('constraint coverage needs review',problems)
        self.assertIn('electrical/library timing checks need review',problems)

    def test_nonfinite_slack_rejected(self):
        path=self.corner/'clock_trials.json';data=json.loads(path.read_text())
        data['trials'][0]['setup_slack_ps']=float('nan');path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):review_corner(self.corner,'TT',[2300,5500])

    def test_removed_reports_rejected(self):
        (self.corner/'check_setup_5500.rpt').unlink()
        with self.assertRaises(FileNotFoundError):review_corner(self.corner,'TT',[2300,5500])

    def test_numerical_disagreement_rejected(self):
        path=self.corner/'clock_trials.json';data=json.loads(path.read_text())
        data['trials'][0]['setup_slack_ps']+=1;path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):review_corner(self.corner,'TT',[2300,5500])

    def test_empty_worst_report_rejected(self):
        path=self.corner/'setup_5500.rpt';path.write_text('')
        with self.assertRaises(ValueError):worst_slack(path,'max')

    def test_relaxed_clock_io_and_exceptions_rejected(self):
        source=(self.corner/'constraints_5500.sdc').read_text()
        check_constraints(source,5500)
        for changed in [source.replace('period 5500.0000','period 6000.0000'),
                        source.replace('-setup 50.0000','-setup 0.0000'),
                        source.replace('-hold 25.0000','-hold 0.0000'),
                        source.replace('set_input_delay 1100.0000','set_input_delay 0.0000'),
                        source.replace('set_output_delay 1100.0000','set_output_delay 0.0000'),
                        source.replace('-pin_load 2.0000','-pin_load 0.0000'),
                        source.replace('set_input_transition 20.0000','set_input_transition 0.0000'),
                        source+'\nset_false_path -from [get_ports A]\n']:
            with self.assertRaises(ValueError):check_constraints(changed,5500)


if __name__=='__main__':unittest.main()
