#!/usr/bin/env python3
"""Evidence admission controls independent of expensive RTL/physical jobs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import experiment_provenance as provenance
from baseline_contract import sha


class Provenance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(provenance, 'ROOT', self.root)
        self.patch.start()
        for name in ['build_experiment_sim.py', 'measure_cpu_experiment.py', 'fma_reference.py']:
            self.write('scripts/'+name, name)
        self.contract = self.write('experiments/test.json', '{}')
        self.experiment = {'experiment_id':'test', 'candidate_rtl_files_sha256':{
            'rtl/execute/fp/rv32_ooo_fp_execute.sv':'a'*64}, 'simulation_inputs_sha256':{'sim.cpp':'b'*64}}
        state = {'commit':'1'*40, 'status':''}
        self.build = {'passed':True,'start':state,'end':state.copy(), 'experiment_id':'test',
            'experiment_manifest_sha256':sha(self.contract),
            'wrapper_sha256':sha(self.root/'scripts/build_experiment_sim.py'),
            'source_sha256':{**self.experiment['candidate_rtl_files_sha256'],**self.experiment['simulation_inputs_sha256']},
            'verilator_version':'Verilator 4.038 pinned', 'gxx_version':'g++ 11.4.0', 'executables':{}, 'records':[]}
        for mode in ['normal','assert']:
            binary=self.write('build/models/'+mode+'/sim',mode)
            command='C "verilator --cc '+('--assert ' if mode=='assert' else '')+'-Wall"'
            generated=self.write('build/models/'+mode+'/Vrv32_ooo_core__verFiles.dat',command+'\n')
            self.build['executables'][mode]={'path':str(binary),'sha256':sha(binary),
                'verFiles_sha256':sha(generated),'verilator_command':command}
            self.build['records'].append({'returncode':0,**self.log('build/'+mode+'-build.log')})
        self.build_path=self.write('build/proof/build.json',json.dumps(self.build))
        self.measurement={'build_summary_sha256':sha(self.build_path),
            'wrapper_sha256':sha(self.root/'scripts/measure_cpu_experiment.py'),
            'simulator_sha256':self.build['executables']['normal']['sha256']}
        self.qual={'passed':True,'start':state,'end':state.copy(),
                   'experiment_manifest_sha256':sha(self.contract),
                   'build_summary_sha256':sha(self.build_path),'records':[]}
        normal=self.build['executables']['normal']['path']
        assertions=self.build['executables']['assert']['path']
        for index in range(18):
            elf=self.write('build/tests/d'+str(index)+'.elf',str(index))
            self.qual['records'].append({'name':'directed-d'+str(index),'passed':True,'elf_sha256':sha(elf),
                'execution':{'command':[normal,'+elf='+str(elf)],'returncode':0,
                             **self.log('build/qualification/d'+str(index)+'.log')}})
        self.suites={
            'spike':{'all_passed':True,'total':18,'passed':18,'results':[
                {'name':str(i),'pass':True,'diff_pass':True} for i in range(18)]},
            'interface':{'passed':True,'simulator_sha256':self.build['executables']['assert']['sha256'],
                'records':[{'name':str(i),'passed':True} for i in range(48)]},
            'memory':{'passed':True,'simulator_sha256':self.build['executables']['assert']['sha256'],
                'reference_simulator_sha256':self.build['executables']['normal']['sha256'],
                'records':[{'name':str(i),'mode':'case','passed':True} for i in range(58)]},
            'fma':{'all_passed':True,'vector_count':3400,
                'simulator_sha256':self.build['executables']['normal']['sha256'],
                'fp_execute_sha256':'a'*64,'oracle_sha256':sha(self.root/'scripts/fma_reference.py'),
                'records':[{'name':'rounding','passed':True},{'name':'finite','passed':True}]}}
        for name,suite in self.suites.items():
            file='diff_results.json' if name=='spike' else 'summary.json'
            summary=self.write('build/qualification/'+name+'/'+file,json.dumps(suite))
            command=['python3','check.py','--sim',assertions if name in ['interface','memory'] else normal,
                     '--out',str(summary.parent)]
            if name=='memory':command+=['--reference-sim',normal]
            self.qual['records'].append({'name':name,'passed':True,'summary_sha256':sha(summary),
                'execution':{'returncode':0,'command':command,**self.log('build/qualification/'+name+'-driver.log')}})
        self.qual_path=self.root/'build/qualification/summary.json'
        self.save_qualification()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def write(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);return path

    def log(self,name):
        path=self.write(name,'Exit status: PASS (0)\n')
        return {'log':str(path),'log_sha256':sha(path)}

    def save_qualification(self):
        self.qual_path.write_text(json.dumps(self.qual))

    def save_build(self):
        self.build_path.write_text(json.dumps(self.build))
        self.measurement['build_summary_sha256']=sha(self.build_path)
        self.qual['build_summary_sha256']=sha(self.build_path);self.save_qualification()

    def check(self):
        return provenance.review_provenance(self.contract,self.experiment,self.measurement,self.build_path,self.qual_path)

    def test_complete_bound_proof(self):
        result,normal=self.check()
        self.assertTrue(result['passed']);self.assertEqual(result['finite_fma_values'],3400)
        self.assertEqual(normal,self.root/'build/models/normal/sim')

    def test_missing_or_wrong_build_and_wrapper(self):
        with self.assertRaises(ValueError):
            provenance.review_provenance(self.contract,self.experiment,self.measurement,None,self.qual_path)
        for field in ['build_summary_sha256','wrapper_sha256','simulator_sha256']:
            with self.subTest(field=field):
                original=self.measurement[field];self.measurement[field]='0'*64
                with self.assertRaises(ValueError):self.check()
                self.measurement[field]=original

    def test_executable_or_generated_mode_change(self):
        binary=self.root/'build/models/normal/sim';original=binary.read_bytes();binary.write_bytes(b'other CPU')
        with self.assertRaises(ValueError):self.check()
        binary.write_bytes(original)
        self.build['executables']['assert']['verilator_command']='C "verilator --cc -Wall"';self.save_build()
        with self.assertRaises(ValueError):self.check()

    def test_dirty_build_or_wrong_source(self):
        self.build['start']['status']=' M rtl.sv';self.save_build()
        with self.assertRaises(ValueError):self.check()
        self.build['start']['status']='';self.build['source_sha256']['sim.cpp']='0'*64;self.save_build()
        with self.assertRaises(ValueError):self.check()

    def test_missing_failed_or_duplicate_qualification(self):
        for change in ['missing','failed','duplicate']:
            original=copy.deepcopy(self.qual)
            with self.subTest(change=change):
                if change=='missing':self.qual['records'].pop()
                if change=='failed':self.qual['records'][0]['passed']=False
                if change=='duplicate':self.qual['records'][1]=copy.deepcopy(self.qual['records'][0])
                self.save_qualification()
                with self.assertRaises(ValueError):self.check()
                self.qual=original
        self.save_qualification()

    def test_suite_count_and_binary_and_raw_log_change(self):
        for name,field,value in [('interface','simulator_sha256','0'*64),('fma','vector_count',3399)]:
            with self.subTest(suite=name):
                file=self.root/'build/qualification'/name/'summary.json';original=file.read_text()
                suite=json.loads(original);suite[field]=value;file.write_text(json.dumps(suite))
                row=next(r for r in self.qual['records'] if r['name']==name);before=row['summary_sha256']
                row['summary_sha256']=sha(file);self.save_qualification()
                with self.assertRaises(ValueError):self.check()
                file.write_text(original);row['summary_sha256']=before
        self.save_qualification()
        (self.root/'build/qualification/d0.log').write_text('different run')
        with self.assertRaises(ValueError):self.check()

    def test_wrong_suite_command(self):
        row=next(r for r in self.qual['records'] if r['name']=='interface')
        row['execution']['command'][3]=self.build['executables']['normal']['path'];self.save_qualification()
        with self.assertRaises(ValueError):self.check()

    def test_measurement_command_binding_and_duplicate_flags(self):
        directory=self.root/'build/measurement/fp32/fir';directory.mkdir(parents=True)
        normal=self.root/'build/models/normal/sim'
        command=[str(normal),'+elf='+str(directory/'input.elf'),'+max-cycles=100000000',
                 '+core-period-ps=9900','+imem-response-ps=10000','+imem-interval-ps=10000',
                 '+dmem-response-ps=10000','+memory-audit='+str(directory/'memory.json'),
                 '+profile-core-roi='+str(directory/'profile.json')]
        record={'execution':{'command':command}}
        provenance.measurement_command(record,normal,directory,9900)
        for extra in ['+core-period-ps=10000','+dmem-latency=1']:
            command.append(extra)
            with self.assertRaises(ValueError):provenance.measurement_command(record,normal,directory,9900)
            command.pop()
        with self.assertRaises(ValueError):provenance.measurement_command(record,normal,directory,10000)

    def test_per_pc_work_preserves_instruction_identity(self):
        a={'pcs':[{'pc':1,'insn':2,'kind':'load','retired':3},{'pc':2,'insn':3,'kind':'load','retired':5}]}
        b=copy.deepcopy(a);b['pcs'][0]['retired']-=1;b['pcs'][1]['retired']+=1
        self.assertNotEqual(provenance.retired_work(a),provenance.retired_work(b))
        a['pcs'].append(copy.deepcopy(a['pcs'][0]))
        with self.assertRaises(ValueError):provenance.retired_work(a)


if __name__=='__main__':unittest.main()
