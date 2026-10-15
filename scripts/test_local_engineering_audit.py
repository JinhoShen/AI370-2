import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import audit_local_engineering_evidence as audit


class AuditTests(unittest.TestCase):
    def fixture(self):
        patch={'patch':'model authored diff'}
        return [
            {'event':'model_response','response':{'choices':[{'message':{'tool_calls':[{'function':{'name':'apply_patch','arguments':json.dumps(patch)}}]}}]}},
            {'event':'tool_result','name':'run_xsim','result':{'ok':False,'exit_code':2}},
            {'event':'tool_call','name':'apply_patch','arguments':patch,'result':{'ok':True}},
            {'event':'tool_result','name':'run_xsim','result':{'ok':True,'exit_code':0,'terminal_pass_marker':True}},
        ]

    def test_accepts_proven_repair_and_rejects_unattributed_patch(self):
        events=self.fixture()
        self.assertEqual(audit.trace_checks(events,'T1',False)['model_authored_accepted_patches'],1)
        events[2]['arguments']={'patch':'human replacement'}
        with self.assertRaisesRegex(ValueError,'model response'):
            audit.trace_checks(events,'T1',False)

    def test_rejects_missing_baseline_and_missing_terminal_marker(self):
        events=self.fixture();events[1]['result']['ok']=True
        with self.assertRaisesRegex(ValueError,'baseline'):
            audit.trace_checks(events,'T1',False)
        events=self.fixture();events[-1]['result']['terminal_pass_marker']=False
        with self.assertRaisesRegex(ValueError,'terminal'):
            audit.trace_checks(events,'T1',False)

    def test_ross_arm_requires_calls_and_control_forbids_them(self):
        events=self.fixture()
        with self.assertRaisesRegex(ValueError,'Ross prerequisite'):
            audit.trace_checks(events,'T1',True)
        events.append({'event':'tool_call','name':'ross_skill_read','result':{'ok':True}})
        with self.assertRaisesRegex(ValueError,'contaminated'):
            audit.trace_checks(events,'T1',False)

    def test_manifest_rejects_mutation_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);f=base/'evidence.txt';f.write_text('actual log')
            (base/'SHA256SUMS').write_text(hashlib.sha256(f.read_bytes()).hexdigest()+'  evidence.txt\n')
            self.assertEqual(audit.manifest(base),1)
            f.write_text('changed log')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                audit.manifest(base)
            (base/'SHA256SUMS').write_text('0'*64+'  ../outside\n')
            with self.assertRaisesRegex(ValueError,'unsafe'):
                audit.manifest(base)


if __name__=='__main__':
    unittest.main()
