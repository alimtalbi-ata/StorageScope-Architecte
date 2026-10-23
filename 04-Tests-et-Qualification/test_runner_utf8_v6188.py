"""Verify the real historical runner executes child tests in UTF-8 mode.

Author: Abdelhalim Talbi. Executes a real subprocess with a temporary checkout.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts' / 'run_historical_windows_suite.py'

class RunnerUTF8Tests(unittest.TestCase):
    def test_child_python_uses_utf8_mode_and_reads_unicode_fixture(self):
        with tempfile.TemporaryDirectory(prefix='ss-utf8-') as td:
            repo=Path(td)/'checkout'
            for name in ('03-Sources','02-Compilation-Windows','04-Tests-et-Qualification'):
                (repo/name).mkdir(parents=True)
            (repo/'04-Tests-et-Qualification'/'accent.txt').write_text('décisions – traçabilité\n',encoding='utf-8')
            (repo/'04-Tests-et-Qualification'/'test_utf8_mode.py').write_text('''import sys,unittest
from pathlib import Path
class UTF8Mode(unittest.TestCase):
 def test_utf8(self):
  self.assertEqual(sys.flags.utf8_mode,1)
  self.assertEqual(Path(__file__).with_name("accent.txt").read_text().strip(),"décisions – traçabilité")
''',encoding='utf-8')
            report=Path(td)/'report.json'
            r=subprocess.run([sys.executable,str(RUNNER),'--repo',str(repo),
                '--minimum-tests','1','--minimum-nested-tests','0','--report',str(report)],
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',check=False)
            self.assertEqual(r.returncode,0,r.stdout)
            evidence=json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(evidence['status'],'PASS')
            self.assertGreaterEqual(evidence['suites'][0]['executed'],1)

if __name__=='__main__':unittest.main()
