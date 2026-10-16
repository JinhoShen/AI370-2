#!/usr/bin/env python3
"""Prepare, or explicitly launch, bounded WAN isolation with an armed restore.

--execute temporarily removes WAN default routes, keeping the NIC/link/profile.
Do not run while unrelated network-dependent work must remain connected.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import run_wan_offline_acceptance as worker


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    routes=worker.routes();devices={r['dev'] for rs in routes.values() for r in rs}
    if len(devices)!=1:raise RuntimeError('Expected exactly one WAN interface; no network modification')
    device=devices.pop()
    uuid=subprocess.check_output(['nmcli','-g','GENERAL.CON-UUID','device','show',device],text=True).strip()
    props=subprocess.check_output(['nmcli','-g','ipv4.never-default,ipv6.never-default','connection','show',uuid],text=True).splitlines()
    if len(props)!=2 or any(p not in ['yes','no'] for p in props):raise RuntimeError('Cannot snapshot exact restore properties')
    out=worker.ROOT/'output/M15/wan-offline'/datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z');out.mkdir(parents=True)
    plan=dict(output=str(out),device=device,connection_uuid=uuid,ipv4=props[0],ipv6=props[1],routes=routes,nic_hash=worker.nic_hash(device),
              restore_unit='ai370-wan-restore-'+out.name.lower(),run_unit='ai370-wan-test-'+out.name.lower())
    worker.write(out/'restore-plan.json',plan);(out/'restore-plan.json').chmod(0o600)
    script=Path(worker.__file__).resolve();shutil.copy2(script,out/'executed-controller.py')
    if not args.execute:
        print('PREPARED_ONLY '+str(out));return 0
    import verify_local_agent_runtime as runtime
    runtime.verify(smoke=False)
    probe=worker.command(['systemd-run','--user','--wait','--pipe','--collect','--unit',plan['restore_unit']+'-probe','/usr/bin/python3',str(script),'--restore-plan',str(out/'restore-plan.json')],timeout=40)
    (out/'restore-permission-probe.log').write_text(probe.stdout+probe.stderr)
    if probe.returncode or not json.loads((out/'restore-result.json').read_text())['persistent_profile_unchanged']:
        raise RuntimeError('Independent systemd restore permission probe failed')
    arm=worker.command(['systemd-run','--user','--collect','--unit',plan['restore_unit'],'--on-active=480s','/usr/bin/python3',str(script),'--restore-plan',str(out/'restore-plan.json')])
    (out/'watchdog-arm.log').write_text(arm.stdout+arm.stderr)
    if arm.returncode:raise RuntimeError('Restore watchdog could not be armed')
    active=worker.command(['systemctl','--user','is-active',plan['restore_unit']+'.timer'])
    if active.returncode:raise RuntimeError('Restore watchdog inactive')
    run=worker.command(['systemd-run','--user','--collect','--unit',plan['run_unit'],'--property','WorkingDirectory='+str(worker.ROOT),
        '--property','RuntimeMaxSec=460','--property','TimeoutStopSec=20','--property','MemorySwapMax=0',
        '/usr/bin/python3',str(script),'--run-plan',str(out/'restore-plan.json')])
    (out/'launch.log').write_text(run.stdout+run.stderr)
    if run.returncode:
        worker.command(['systemctl','--user','stop',plan['restore_unit']+'.timer'])
        raise RuntimeError('Offline worker launch failed; network was not changed')
    print('OFFLINE_TEST_LAUNCHED '+str(out));return 0


if __name__=='__main__':raise SystemExit(main())
