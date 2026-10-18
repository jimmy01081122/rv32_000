#!/usr/bin/env python3
"""A lost tool session must not become a successful physical result."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from run_physical_job import execute


class Worker(unittest.TestCase):
    def run_job(self, code, initial_digest=None):
        directory=Path(self.directory.name)
        source=directory/'input.txt';source.write_text('frozen')
        report=directory/'run.json';report.write_text(json.dumps({'passed':False}))
        spec=directory/'job.json';spec.write_text(json.dumps({
            'report':str(report),'log':str(directory/'make.log'),'cwd':str(directory),
            'inputs':{str(source):initial_digest or hashlib.sha256(source.read_bytes()).hexdigest()},
            'command':[sys.executable,'-c',code]}))
        result=execute(spec)
        return result,json.loads(report.read_text()),directory

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()

    def tearDown(self):
        self.directory.cleanup()

    def test_success_still_requires_closure_review(self):
        result,report,directory=self.run_job('print("complete")')
        self.assertEqual(result,0)
        self.assertEqual(report['returncode'],0)
        self.assertTrue(report['flow_completed'])
        self.assertFalse(report['passed'])
        self.assertEqual((directory/'make.log').read_text(),'complete\n')

    def test_nonzero_exit_is_retained(self):
        result,report,_=self.run_job('raise SystemExit(7)')
        self.assertEqual(result,1)
        self.assertEqual(report['returncode'],7)
        self.assertFalse(report['flow_completed'])

    def test_input_change_rejects_zero_exit(self):
        result,report,_=self.run_job('from pathlib import Path; Path("input.txt").write_text("changed")')
        self.assertEqual(result,1)
        self.assertEqual(report['returncode'],0)
        self.assertFalse(report['flow_completed'])
        self.assertFalse(report['input_identities_unchanged'])

    def test_stale_inputs_prevent_launch(self):
        result,report,directory=self.run_job('from pathlib import Path; Path("sentinel").touch()',initial_digest='0'*64)
        self.assertEqual(result,1)
        self.assertEqual(report['job_state'],'failed')
        self.assertFalse((directory/'sentinel').exists())

    def test_duplicate_launch_cannot_overwrite(self):
        _,report,directory=self.run_job('print("first")')
        with self.assertRaises(FileExistsError):execute(directory/'job.json')
        self.assertEqual(json.loads((directory/'run.json').read_text()),report)
        self.assertEqual((directory/'make.log').read_text(),'first\n')


if __name__=='__main__':unittest.main()
