#!/usr/bin/env python3
"""Reject baseline drift, unauthorized RTL, stale candidates and changed memory."""
import copy
import os
from pathlib import Path
import unittest
from baseline_contract import load,check_rtl
from experiment_contract import load_experiment,validate_experiment

CONTRACT=Path('experiments')/os.environ.get('CPU_EXPERIMENT','lsu-a-v1')/'manifest.json'


class Experiment(unittest.TestCase):
    def test_complete_authorized_contract(self):
        _,baseline=load_experiment(CONTRACT)
        self.assertEqual(baseline['state'],'frozen')

    def test_baseline_gate_rejects_candidate(self):
        with self.assertRaisesRegex(ValueError,'baseline RTL changed'):check_rtl(load())

    def test_other_candidate_rejected(self):
        other='lsu-b-v1' if CONTRACT.parent.name=='lsu-a-v1' else 'lsu-a-v1'
        with self.assertRaisesRegex(ValueError,'live candidate RTL changed'):
            load_experiment(Path('experiments')/other/'manifest.json')

    def test_drift_rejected(self):
        original,_=load_experiment(CONTRACT)
        mutations=[('baseline_manifest_sha256','0'*64),('baseline_commit','0'*40),
                   ('allowed_rtl_changes',['rtl/lsu/rv32_ooo_lsu.sv','rtl/core/rv32_ooo_core.sv']),
                   ('memory_ps',9999),('state','implementing'),('experiment_id','lsu-ab-v1')]
        for field,value in mutations:
            with self.subTest(field=field):
                x=copy.deepcopy(original);x[field]=value
                with self.assertRaises(ValueError):validate_experiment(x)
        for field,name in [('candidate_rtl_files_sha256','rtl/lsu/rv32_ooo_lsu.sv'),
                           ('candidate_rtl_files_sha256','rtl/core/rv32_ooo_core.sv'),
                           ('simulation_inputs_sha256','sim/tb/sim_main.cpp'),
                           ('physical_inputs_sha256','physical/asap7/baseline/config.mk')]:
            with self.subTest(field=field,name=name):
                x=copy.deepcopy(original);x[field][name]='0'*64
                with self.assertRaises(ValueError):validate_experiment(x)
        x=copy.deepcopy(original);x['planning_targets']['standard_cell_area_ratio_max']=1.2
        with self.assertRaises(ValueError):validate_experiment(x)


if __name__=='__main__':unittest.main()
