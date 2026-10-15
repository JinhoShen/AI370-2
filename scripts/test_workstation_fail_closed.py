"""Exercise the actual shell guard with a mismatched dpkg fixture, no workloads."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class FailClosedTests(unittest.TestCase):
    def test_protected_mismatch_prevents_every_timed_workload(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);bin_dir=base/'bin';bin_dir.mkdir()
            for name,body in [('dpkg-query','printf unapproved-version'),('timeout','touch "$AI370_TEST_WORKLOAD_MARKER"; exit 99')]:
                p=bin_dir/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
            env=os.environ.copy();env.update(PATH=str(bin_dir)+':'+env['PATH'],AI370_M14_OUTPUT_ROOT=str(base/'output'),AI370_TEST_WORKLOAD_MARKER=str(base/'workload-started'))
            run=subprocess.run(['bash',str(ROOT/'scripts/verify_m14_workstation.sh')],env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,1,run.stdout+run.stderr)
            self.assertFalse((base/'workload-started').exists())
            summary=json.loads(next((base/'output').glob('*/summary.json')).read_text())
            self.assertEqual(summary['overall'],'FAIL')
            self.assertTrue(summary['stopped_before_workloads'])
            self.assertEqual([c['name'] for c in summary['checks']],['system inventory','protected stack versions','remaining workload/readiness checks'])


if __name__=='__main__':
    unittest.main()
