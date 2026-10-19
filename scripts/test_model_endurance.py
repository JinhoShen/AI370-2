import unittest
from collections import Counter
import run_model_endurance as e


class EnduranceTests(unittest.TestCase):
    def test_four_existing_nonretired_models_three_trials_per_task_arm(self):
        rows=list(e.schedule())
        self.assertEqual(len(rows),72)
        counts=Counter((m['id'],t,a) for r,m,t,a in rows)
        self.assertEqual(set(counts.values()),{3})
        self.assertTrue(all('Qwen3.6' not in m['id'] for _,m,_,_ in rows))
        self.assertEqual(rows[0][1]['id'],'Qwen3.8-27B-UD-Q4_K_M')

    def test_gemma_is_explicit_cpu_profile_not_hidden_fallback(self):
        m=next(m for m in e.roster() if m['id'].startswith('gemma'))
        cmd=e.server_command(m)
        self.assertIn('build-cpu',cmd[0])
        self.assertEqual(cmd[cmd.index('--n-gpu-layers')+1],'0')
        self.assertEqual(cmd[cmd.index('--ctx-size')+1],'16384')
        self.assertNotIn('--save-options',cmd)

    def test_severe_kernel_gate_never_reinitializes_formal_gpu(self):
        self.assertFalse(e.restoration_allowed('SAFETY_OR_CONTROLLER_BLOCK: SafetyFault: KERNEL_FAULT_OR_UNREADABLE'))
        self.assertFalse(e.restoration_allowed('PROTECTED_STACK_CHANGED'))
        self.assertTrue(e.restoration_allowed('USER_STOP'))

    def test_manifest_function_is_not_shadowed_in_controller_scope(self):
        import symtable
        from pathlib import Path
        table=symtable.symtable(Path(e.__file__).read_text(),e.__file__,'exec')
        main=next(t for t in table.get_children() if t.get_name()=='main')
        self.assertTrue(main.lookup('manifest').is_global())

    def test_real_manifest_generation_and_verification(self):
        import tempfile,hashlib
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'source.v').write_text('module sample; endmodule\n')
            e.manifest(path)
            self.assertEqual((path/'SHA256SUMS').read_text(),hashlib.sha256((path/'source.v').read_bytes()).hexdigest()+'  source.v\n')

    def test_summary_keeps_failed_and_timeout_trials(self):
        rows=[dict(model='m',task='T1',arm='B',status=s,elapsed_seconds=t) for s,t in [('PASS',10),('FAIL',20),('TIMEOUT',30)]]
        row=e.summarize(rows)[0]
        self.assertEqual(row['attempts'],3)
        self.assertEqual(row['passes'],1)
        self.assertEqual(row['mean_all_attempt_seconds'],20)
        self.assertEqual(row['statuses'],['PASS','FAIL','TIMEOUT'])


if __name__=='__main__':unittest.main()
