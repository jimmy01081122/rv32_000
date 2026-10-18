#!/usr/bin/env python3
import copy
from pathlib import Path
import tempfile
import unittest
from baseline_contract import load,validate,check_rtl,image_end
class Contract(unittest.TestCase):
    def test_complete_reference(self):
        contract=load();self.assertEqual(len(validate(contract)),27);check_rtl(contract)
    def test_missing_or_duplicate_workload_rejected(self):
        for action in ('missing','duplicate'):
            contract=load()
            if action=='missing':contract['workloads'].pop()
            else:contract['workloads'][-1]=copy.deepcopy(contract['workloads'][0])
            with self.assertRaises(ValueError):validate(contract)
    def test_policy_or_group_change_rejected(self):
        contract=load();contract['memory']['policy']='fixed_cycles'
        with self.assertRaises(ValueError):validate(contract)
        contract=load();contract['workloads'][0]['group']='matrix_ml'
        with self.assertRaises(ValueError):validate(contract)
    def test_wrong_rtl_digest_rejected(self):
        contract=load();key=next(iter(contract['rtl_files_sha256']));contract['rtl_files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):check_rtl(contract)
    def test_bad_elf_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.elf';path.write_bytes(b'not an ELF')
            with self.assertRaises(ValueError):image_end(path)
    def test_fixture_identity_or_tolerance_change_rejected(self):
        for field,value in [('fixture_sha256','0'*64),('absolute_tolerance',1),
                            ('relative_tolerance',1),('dimensions',{'samples':1})]:
            contract=load();row=next(r for r in contract['workloads'] if r['family']=='fp32')
            row[field]=value
            with self.assertRaises(ValueError):validate(contract)
if __name__=='__main__':unittest.main()
