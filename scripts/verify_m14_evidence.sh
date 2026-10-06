#!/usr/bin/env bash
# Read-only evidence and protected-stack audit. Does not run accelerator workloads.
set -uo pipefail
project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project"
stamp="$(date +%Y%m%dT%H%M%S%z)"
out="$project/output/M14/evidence-audit/$stamp"
mkdir -p "$out"
checks="$out/checks.tsv"
: > "$checks"
fails=0
defers=0
record() {
  local state="$1" name="$2" detail="$3"
  printf '%-9s %s — %s\n' "$state" "$name" "$detail"
  printf '%s\t%s\t%s\n' "$state" "$name" "$detail" >> "$checks"
  case "$state" in FAIL) fails=$((fails+1));; DEFERRED|NOT_TESTED) defers=$((defers+1));; esac
}
check_file() {
  if [[ -s "$2" ]]; then record PASS "$1" "present: ${2#$project/}"; else record FAIL "$1" "missing/empty: ${2#$project/}"; fi
}
check_pkg() {
  local name="$1" expected="$2" actual
  actual="$(dpkg-query -W -f='${Version}' "$name" 2>/dev/null || true)"
  printf '%s\t%s\t%s\n' "$name" "$expected" "${actual:-MISSING}" >> "$out/protected-stack.tsv"
  if [[ "$actual" == "$expected" ]]; then record PASS "protected package $name" "$actual"; else record FAIL "protected package $name" "expected $expected; found ${actual:-MISSING}"; fi
}

printf 'M14 evidence audit\nstarted=%s\nhead=%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" > "$out/run-metadata.txt"

if git diff --check && git diff --cached --check; then record PASS 'Git whitespace check' 'working diffs pass git diff --check'; else record FAIL 'Git whitespace check' 'see git diff --check output'; fi

if sha256sum -c docs/M11/evidence/post-program-regression-2026-10-02/SHA256SUMS > "$out/m11-regression-checksums.log" 2>&1; then record PASS 'M11 regression evidence integrity' 'all listed files match saved SHA256'; else record FAIL 'M11 regression evidence integrity' 'checksum verification failed'; fi
if (cd docs/M12/evidence/host-fpga-jtag-axi-20261002 && sha256sum -c SHA256SUMS) > "$out/m12-checksums.log" 2>&1; then record PASS 'M12 build/transaction evidence integrity' 'all listed files match saved SHA256'; else record FAIL 'M12 build/transaction evidence integrity' 'checksum verification failed'; fi
if (cd docs/M13/evidence/2026-10-02 && sha256sum -c M12_WORKFLOW_SHA256SUMS) > "$out/m13-workflow-checksums.log" 2>&1 && (cd docs/M13/evidence/2026-10-02/hls-skill-smoke && sha256sum -c SHA256SUMS) > "$out/m13-hls-checksums.log" 2>&1; then record PASS 'M13 local-KB/HLS skill evidence integrity' 'workflow and HLS skill outputs match saved SHA256'; else record FAIL 'M13 local-KB/HLS skill evidence integrity' 'checksum verification failed'; fi
qwen_evidence="$project/docs/M13/evidence/2026-10-06/local-qwen-codex-fpga-loop"
if (cd "$qwen_evidence" && sha256sum -c SHA256SUMS) > "$out/m13-local-qwen-checksums.log" 2>&1 && rg -q 'TEST_PASS baseline_and_selected_mode=1' "$qwen_evidence/logs/xsim-patched-network-sandbox.log" && rg -q 'VALIDATION_PASS .*xsim=PASS vivado_synthesis=PASS' "$qwen_evidence/logs/validation-summary.txt" && [[ -s "$qwen_evidence/reports/utilization-summary.txt" && -s "$qwen_evidence/reports/timing-summary.txt" ]]; then record PASS 'M13 local Qwen RTL/XSim/Vivado evidence' 'model-authored source, XSim/Vivado markers and report summaries match the retained SHA256 manifest'; else record FAIL 'M13 local Qwen RTL/XSim/Vivado evidence' 'manifest, verification marker, or report summary missing/invalid'; fi

check_file 'M11 DDR report' "$project/docs/M11/SP701_DDR3_Memory_Test_Report.md"
check_file 'M12 source build flow' "$project/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/build.tcl"
check_file 'M12 retained physical transcript' "$project/docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log"
if rg -q 'M12_AXI_LOOPBACK_TRANSFORM=PASS' docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log && rg -q 'M12_POSTTEST_JTAG=PASS' docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log; then record PASS 'M12 physical transaction record' 'four expected AXI loopback vectors and post-test JTAG marker found'; else record FAIL 'M12 physical transaction record' 'expected physical transaction markers missing'; fi
check_file 'M13 HLS C simulation transcript' "$project/docs/M13/evidence/2026-10-02/hls-skill-smoke/vitis-run-csim.log"
check_file 'M13 HLS synthesis report' "$project/docs/M13/evidence/2026-10-02/hls-skill-smoke/csynth.rpt"
if rg -q 'PASS: 4 HLS C simulation vectors matched' docs/M13/evidence/2026-10-02/hls-skill-smoke/vitis-run-csim.log && rg -q "Target device:  xc7s100-fgga676-2" docs/M13/evidence/2026-10-02/hls-skill-smoke/csynth.rpt; then record PASS 'M13 HLS skill evidence' 'bounded csim PASS and Spartan-7-targeted csynth report present'; else record FAIL 'M13 HLS skill evidence' 'expected C simulation or synthesis marker missing'; fi
if (cd docs/M14/evidence/2026-10-02/m12-clean-rebuild && sha256sum -c SHA256SUMS) > "$out/m12-clean-rebuild-checksums.log" 2>&1 && rg -q 'write_bitstream completed successfully' docs/M14/evidence/2026-10-02/m12-clean-rebuild/vivado-build.log && rg -q 'WNS\(ns\).*TNS\(ns\)' docs/M14/evidence/2026-10-02/m12-clean-rebuild/timing-summary-routed.rpt && rg -q 'All user specified timing constraints are met' docs/M14/evidence/2026-10-02/m12-clean-rebuild/timing-summary-routed.rpt && rg -q 'DRC finished with 0 Errors' docs/M14/evidence/2026-10-02/m12-clean-rebuild/vivado-build.log; then record PASS 'M12 clean software rebuild' 'Vivado bitstream build, routed DRC and timing evidence checksums verified; no FPGA programming'; else record FAIL 'M12 clean software rebuild' 'clean-build evidence missing, altered, or incomplete'; fi
if PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts -p 'test_apt_change_guard.py' -v > "$out/apt-guard-tests.log" 2>&1; then record PASS 'APT protected-stack guard tests' 'parser fixture tests passed without package changes'; else record FAIL 'APT protected-stack guard tests' 'see apt-guard-tests.log'; fi
if python3 - docs/M14/evidence/2026-10-02/apt-guard/safe-userspace-simulation.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
assert r['verdict']=='SAFE_SIMULATION' and not r['protected_changes']
assert r['actions'] and all(not a['protected'] for a in r['actions'])
PY
then record PASS 'APT safe transaction simulation evidence' 'cowsay was simulated as userspace-only; no package was installed'; else record FAIL 'APT safe transaction simulation evidence' 'saved simulation did not meet guard assertions'; fi
record DEFERRED 'APT protected-change live simulation' 'protected transaction classification is covered by negative parser fixtures; no real protected package transaction was requested'
record DEFERRED 'M12 XRT host application' 'SP701 .xpfm and XRT C++ development headers are absent; system XRT stays protected for NPU'
record DEFERRED 'M13 local answer-model / air-gap' 'local KB retrieval is verified; answer-model plus client end-to-end isolation remains untested'
record DEFERRED 'M0.1 full recovery' 'file-level checkpoint exists; off-device and full restore validation remain outstanding'
record NOT_TESTED 'M15 unified regression' 'intentionally not run by this read-only evidence audit'

printf '\n[protected stack read-only guard]\n'
check_pkg "linux-image-$(uname -r)" '6.17.0-14.14~24.04.1'
check_pkg mesa-vulkan-drivers '25.2.8-0ubuntu0.24.04.1'
check_pkg libdrm-amdgpu1 '2.4.125-1ubuntu0.1~24.04.1'
check_pkg rocm-core '7.2.1.70201-81~24.04'
check_pkg hip-runtime-amd '7.2.53211.70201-81~24.04'
check_pkg xrt-base '2.21.75'
check_pkg xrt-npu '2.21.75'
check_pkg xrt_plugin-amdxdna '2.21'
module_path="$(modinfo -n amdxdna 2>/dev/null || true)"
module_version="$(cat /sys/module/amdxdna/version 2>/dev/null || true)"
printf 'amdxdna_module_path=%s\namdxdna_module_version=%s\n' "$module_path" "$module_version" >> "$out/protected-stack.tsv"
if [[ "$module_path" == */updates/dkms/amdxdna.ko* && "$module_version" == 2.21.260102.53.release* ]]; then record PASS 'amdxdna protected module' "$module_version (DKMS path)"; else record FAIL 'amdxdna protected module' "path=$module_path version=$module_version"; fi

python3 - "$out/summary.json" "$out/run-metadata.txt" "$checks" "$fails" "$defers" <<'PY'
import csv, json, sys
summary_path, metadata_path, checks_path, failures, deferred = sys.argv[1:]
metadata={}
with open(metadata_path,encoding='utf-8') as f:
    for line in f:
        if '=' in line:
            k,v=line.rstrip('\n').split('=',1); metadata[k]=v
with open(checks_path,encoding='utf-8',newline='') as f:
    checks=[{'status':r[0],'name':r[1],'detail':r[2]} for r in csv.reader(f,delimiter='\t')]
obj={'schema':'ai370-m14-evidence-audit/v1','captured_at':metadata.get('started'),'head':metadata.get('head'),'overall':'FAIL' if int(failures) else ('PASS_WITH_DEFERRED' if int(deferred) else 'PASS'),'fail_count':int(failures),'deferred_or_not_tested_count':int(deferred),'execution_policy':'read-only evidence/package/module checks; no GPU/NPU/LLM workload or FPGA programming','checks':checks}
with open(summary_path,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
PY
printf 'Summary: %s\n' "$out/summary.json"
(( fails == 0 ))
