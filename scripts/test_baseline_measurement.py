#!/usr/bin/env python3
"""Negative controls for accepting a complete physical-time baseline record."""
import copy
from pathlib import Path
import struct
import tempfile
import unittest
from measure_post_lsu_baseline import check_result


class Measurement(unittest.TestCase):
    def test_record_and_corrupted_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            elf = Path(directory)/'input.elf'
            header = bytearray(52)
            header[:7] = b'\x7fELF\x01\x01\x01'
            struct.pack_into('<I', header, 28, 52)
            struct.pack_into('<HH', header, 42, 32, 1)
            elf.write_bytes(header+struct.pack('<8I',1,0,0x80000000,0,0,4096,0,0))
            row = {'family':'embench','reference_cycles':41}
            text = 'Exit status    : PASS (0)\nBenchmark executed in cycles: 41\n'
            audit = {'fixed_time':True,'core_period_ps':5500,
                     'imem_response_ps':5500,'imem_interval_ps':5500,
                     'dmem_response_ps':5500,'stack_pointer_seen':True,
                     'minimum_retired_sp':0x800ffff0}
            for port in ('imem','dmem'):
                audit.update({port+'_requests':20,port+'_responses':19,
                              port+'_min_response_ps':5500,port+'_max_response_ps':5500})
            profile = {'cycles':41,'trace_mismatches':0,'layout_mismatches':0,
                       'cycle_partition':{'retire':30,'wait':11}}
            def problems(a=audit,p=profile,t=text):
                return check_result(row,t,a,5500,5500,elf,p)['problems']
            self.assertEqual(problems(),[])
            for key,value in [('fixed_time',False),('core_period_ps',3000),
                              ('dmem_response_ps',1),('imem_interval_ps',1),
                              ('imem_responses',21),('dmem_responses',0),
                              ('dmem_min_response_ps',5499),('imem_max_response_ps',11000),
                              ('minimum_retired_sp',0x80000000)]:
                with self.subTest(corruption=key):
                    broken=copy.deepcopy(audit);broken[key]=value
                    self.assertTrue(problems(a=broken))
            for key,value in [('cycles',40),('trace_mismatches',1),
                              ('layout_mismatches',1),('cycle_partition',{'retire':30})]:
                with self.subTest(corruption=key):
                    broken=copy.deepcopy(profile);broken[key]=value
                    self.assertTrue(problems(p=broken))
            self.assertTrue(problems(t=text+'TRAP encountered\n'))


if __name__=='__main__':
    unittest.main()
