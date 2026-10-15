#!/usr/bin/env bash
# Bounded software validation, not deployment or physical-airgap certification.
# Reuse resident formal Qwen. No new model process, retired model or CPU cap.
set -uo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
out="$repo/output/M15/unified-$(date +%Y%m%dT%H%M%S%z)"
mkdir -p "$out"
started="$(date --iso-8601=seconds)"
printf 'started=%s\nhead=%s\n' "$started" "$(git rev-parse HEAD)" > "$out/run-metadata.txt"
finish() {
  local code=$?
  if [[ ! -f "$out/summary.json" ]]; then
    python3 - "$out" "$started" "$code" <<'PY'
import csv,json,sys
from pathlib import Path
out=Path(sys.argv[1]);status=out/'status.tsv'
rows=list(csv.reader(status.open(),delimiter='\t')) if status.exists() else []
(out/'summary.json').write_text(json.dumps(dict(status='FAIL',started=sys.argv[2],exit_code=int(sys.argv[3]),checks=rows,
    m15='PRE-FINAL',final_golden=False,scope='stopped at first failing gate; inspect logs'),indent=2)+'\n')
print('FAIL evidence: '+str(out))
PY
  fi
}
trap finish EXIT
capture() {
  local name="$1"; shift
  if "$@" > "$out/$name.log" 2>&1; then
    printf 'PASS\t%s\n' "$name" | tee -a "$out/status.tsv"
  else
    local code=$?
    printf 'FAIL\t%s\texit %s\n' "$name" "$code" | tee -a "$out/status.tsv"
    return "$code"
  fi
}
# Any protected-stack/device failure stops the suite before further work.
capture workstation bash scripts/verify_m14_workstation.sh || exit 1
capture evidence bash scripts/verify_m14_evidence.sh || exit 1
capture local-engineering python3 scripts/audit_local_engineering_evidence.py --output "$out/engineering-evidence.json" || exit 1
capture formal-local-ai python3 scripts/verify_local_agent_runtime.py --output "$out/formal-runtime.json" || exit 1
capture hls-version bash -c 'source /home/shen/tools/Xilinx/2026.1/2026.1/Vitis/settings64.sh >/dev/null 2>&1; vitis-run --version' || exit 1
if ! journalctl -k --since "$started" --no-pager -o short-iso > "$out/kernel.log" 2> "$out/kernel-read-error.txt"; then
  printf 'FAIL\tkernel log unreadable\n' >> "$out/status.tsv"
  exit 1
fi
if rg -i 'amdgpu.*(page fault|vm_validate|not enough memory|device lost|reset|ring timeout|error)|TTM.*(corrupt|error)|soft lockup|amdxdna.*(error|fault|timeout)|oom-kill|Out of memory: Killed' "$out/kernel.log" > "$out/kernel-faults.log"; then
  printf 'FAIL\tkernel fault\n' >> "$out/status.tsv"
  exit 1
else
  code=$?
  if [[ "$code" != 1 ]]; then
    printf 'FAIL\tkernel pattern audit error\n' >> "$out/status.tsv"
    exit 1
  fi
fi
printf 'PASS\tkernel audit\n' >> "$out/status.tsv"
python3 - "$out" "$started" <<'PY'
import csv,json,sys
from datetime import datetime
from pathlib import Path
out=Path(sys.argv[1]);rows=list(csv.reader((out/'status.tsv').open(),delimiter='\t'))
result=dict(status='SOFTWARE_PASS_WITH_DEFERRED',started=sys.argv[2],completed=datetime.now().astimezone().isoformat(),
            scope='bounded current software regression; reuse resident ENGINEERING model, no FPGA programming',checks=rows,
            m15='PRE-FINAL',final_golden=False,
            deferred=['T7 media on user hold','clean-target rebuild/full boot restore NOT_TESTED',
                      'full physically disconnected workflow NOT_TESTED','Telegram WAITING_USER credential',
                      'M7.1 retired Qwen3.6 OPEN; not run','M8 NPU LLM DEFERRED','broader Vitis IDE/direct Vivado Tcl agent scope NOT_TESTED'],
            not_required=['350 GB current-state image','copy of installed Xilinx tree'])
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],evidence=str(out),m15=result['m15'])))
PY
