import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_wan_offline_acceptance as offline


class SafetyTests(unittest.TestCase):
    def test_unarmed_restore_timer_refuses_network_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan=dict(output=tmp,restore_unit='fixture',device='not-used')
            def command(args,timeout=25):
                self.assertNotEqual(args[0],'nmcli')
                return subprocess.CompletedProcess(args,1,'inactive','')
            with patch.object(offline,'command',side_effect=command):
                self.assertEqual(offline.run(plan),1)
            result=json.loads((Path(tmp)/'result.json').read_text())
            self.assertEqual(result['network_restoration'],'NOT_NEEDED')
            self.assertIn('timer not active',result['error'])

    def test_restore_uses_only_temporary_device_modify_and_checks_saved_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan=dict(output=tmp,device='fixture0',ipv4='no',ipv6='no',connection_uuid='fixture')
            responses=[subprocess.CompletedProcess([],0,'ok',''),subprocess.CompletedProcess([],0,'no\nno\n','')]
            with patch.object(offline,'command',side_effect=responses) as call,patch.object(offline,'routes',return_value={'-4':[{}],'-6':[]}):
                result=offline.restore(plan)
            self.assertEqual(call.call_args_list[0].args[0],['nmcli','--wait','20','device','modify','fixture0','ipv4.never-default','no','ipv6.never-default','no'])
            self.assertTrue(result['persistent_profile_unchanged'])


if __name__=='__main__':unittest.main()
