#!/usr/bin/env python3
"""Absolute-time deadline/credit/ordering checks, independent of CPU cycle count."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MemoryTime(unittest.TestCase):
    def test_deadlines_order_and_backpressure(self):
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'time-check'
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                            '-Isim/tb','sim/tb/test_fixed_time_memory.cpp','-o',str(exe)],cwd=ROOT,check=True)
            subprocess.run([str(exe)],check=True)
if __name__=='__main__':unittest.main()
