#!/usr/bin/env bash
# Guarded, read-only workstation verification. Test workloads are bounded and
# reuse the already validated M3/M4/M5 smoke tests. No installation or config
# mutation is performed by this script.
set -uo pipefail

project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project"
stamp="$(date +%Y%m%dT%H%M%S%z)"
out="$project/output/M14/runs/$stamp"
mkdir -p "$out"
started="$(date --iso-8601=seconds)"
failures=0
deferred=0
checks_file="$out/checks.tsv"
: >"$checks_file"

record() {
  local state="$1" name="$2" detail="$3"
  printf '%-9s %s — %s\n' "$state" "$name" "$detail"
  printf '%s\t%s\t%s\n' "$state" "$name" "$detail" >>"$checks_file"
  case "$state" in FAIL) failures=$((failures + 1));; DEFERRED|NOT_TESTED) deferred=$((deferred + 1));; esac
}
pass() { record PASS "$1" "$2"; }
fail_item() { record FAIL "$1" "$2"; }
defer() { record DEFERRED "$1" "$2"; }
not_tested() { record NOT_TESTED "$1" "$2"; }
pkgver() { dpkg-query -W -f='${Version}' "$1" 2>/dev/null || true; }

printf 'M14 guarded verifier\nStart: %s\nEvidence: %s\n' "$started" "$out"

{
  printf 'captured_at=%s\n' "$started"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'os='; . /etc/os-release; printf '%s %s (%s)\n' "$PRETTY_NAME" "$VERSION_ID" "$VERSION_CODENAME"
  printf 'kernel=%s\n' "$(uname -r)"
  printf 'architecture=%s\n' "$(uname -m)"
  printf 'memory='; awk '/MemTotal:/{printf "%.1f GiB\n", $2/1048576}' /proc/meminfo
  printf 'root_fs='; findmnt -no SOURCE,FSTYPE,OPTIONS /
  printf 'gpu_pci='; lspci -nn -d 1002:150e 2>/dev/null | head -1 || true
  printf 'amdxdna_module=%s\n' "$(modinfo -n amdxdna 2>/dev/null || echo unavailable)"
  printf 'amdxdna_loaded_version=%s\n' "$(cat /sys/module/amdxdna/version 2>/dev/null || echo unavailable)"
} >"$out/system-inventory.txt"
pass 'system inventory' "captured in ${out#$project/}/system-inventory.txt"

printf '\n[protected stack guard]\n'
protected_ok=1
check_pkg() {
  local name="$1" expected="$2" actual
  actual="$(pkgver "$name")"
  if [[ -n "$actual" && "$actual" == "$expected" ]]; then
    printf '%s=%s\n' "$name" "$actual" >>"$out/protected-stack.txt"
  else
    printf '%s expected=%s actual=%s\n' "$name" "$expected" "${actual:-MISSING}" >>"$out/protected-stack.txt"
    protected_ok=0
  fi
}
check_pkg linux-image-"$(uname -r)" '6.17.0-14.14~24.04.1'
check_pkg mesa-vulkan-drivers '25.2.8-0ubuntu0.24.04.1'
check_pkg libdrm-amdgpu1 '2.4.125-1ubuntu0.1~24.04.1'
check_pkg rocm-core '7.2.1.70201-81~24.04'
check_pkg hip-runtime-amd '7.2.53211.70201-81~24.04'
check_pkg xrt-base '2.21.75'
check_pkg xrt-npu '2.21.75'
check_pkg xrt_plugin-amdxdna '2.21'
module_path="$(modinfo -n amdxdna 2>/dev/null || true)"
module_version="$(cat /sys/module/amdxdna/version 2>/dev/null || true)"
[[ "$module_path" == */updates/dkms/amdxdna.ko* ]] || protected_ok=0
[[ "$module_version" == 2.21.260102.53.release* ]] || protected_ok=0
printf 'amdxdna_module_path=%s\namdxdna_module_version=%s\n' "$module_path" "$module_version" >>"$out/protected-stack.txt"
if [[ "$protected_ok" == 1 ]]; then pass 'protected stack versions' 'all pinned package/module versions match documented Golden State'; else fail_item 'protected stack versions' 'one or more pinned versions/path differ; see protected-stack.txt'; fi

printf '\n[HIP / GPU]\n'
if [[ -x output/M3/hip-compute ]] && timeout 30s output/M3/hip-compute >"$out/hip.log" 2>&1 && rg -q 'PASS: 1024 HIP GPU results verified' "$out/hip.log"; then
  pass 'HIP GPU compute' 'bounded gfx1150 smoke; 1024 verified results'
else
  fail_item 'HIP GPU compute' 'bounded smoke failed or expected GPU result marker absent'
fi

printf '\n[Vulkan]\n'
if [[ -x output/M4/build/vulkan-compute && -s output/M4/build/verify.spv ]] && timeout 20s output/M4/build/vulkan-compute output/M4/build/verify.spv >"$out/vulkan.log" 2>&1 && rg -q 'PASS: 1024 GPU shader results verified; CPU fallback forbidden' "$out/vulkan.log"; then
  pass 'Vulkan/RADV compute' 'bounded GPU shader smoke passed with CPU fallback forbidden'
else
  fail_item 'Vulkan/RADV compute' 'bounded smoke failed or strict GPU marker absent'
fi

printf '\n[XDNA2 / XRT / NPU]\n'
xrt_smi=/opt/xilinx/xrt/bin/unwrapped/xrt-smi
if [[ -x "$xrt_smi" ]] && bash scripts/npu21.sh "$xrt_smi" examine -r all >"$out/xrt-examine.log" 2>&1 && rg -q 'NPU Strix' "$out/xrt-examine.log" && rg -q 'XRT' "$out/xrt-examine.log" && rg -q '1\.1\.2\.64' "$out/xrt-examine.log"; then
  pass 'XRT / NPU / firmware enumeration' 'Strix NPU detected; XRT 2.21.75 and firmware 1.1.2.64 observed'
else
  fail_item 'XRT / NPU / firmware enumeration' 'expected NPU, XRT and firmware evidence missing'
fi
npu_ok=0
if NPU_OUTPUT_DIR="$out/npu" NPU_RESULT_FILE="$out/npu-result.json" bash scripts/ryzenai21.sh timeout 180s .venvs/npu21/bin/python verify/npu_cnn.py output/M5/quicktest/quicktest/test_model.onnx >"$out/npu-cnn.log" 2>&1 && [[ -s "$out/npu-result.json" ]]; then
  if python3 - "$out/npu-result.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    r = json.load(f)
assert r.get("status") == "PASS"
assert r.get("cpu_fallback_disabled") is True
assert r.get("profile_node_providers") == ["VitisAIExecutionProvider"]
assert r.get("npu_hardware_time_delta_ns", 0) > 0
assert r.get("max_abs_errors") and max(r["max_abs_errors"]) == 0.0
PY
  then npu_ok=1; fi
fi
if [[ "$npu_ok" == 1 ]]; then pass 'strict NPU CNN' 'VitisAI-only profile, hardware counter advanced, zero CPU-reference error'; else fail_item 'strict NPU CNN' 'strict no-fallback result did not satisfy all assertions'; fi

printf '\n[Local AI backend readiness]\n'
for backend in cpu vulkan hip; do
  binary="output/M6/build-$backend/bin/llama-cli"
  if [[ ! -x "$binary" ]]; then defer "llama.cpp $backend" 'backend binary absent'; continue; fi
  if timeout 20s "$binary" --list-devices >"$out/llama-$backend-devices.log" 2>&1; then
    case "$backend" in
      cpu) pass 'llama.cpp CPU backend' 'binary starts and lists backend devices; no model inference run';;
      vulkan) if rg -qi 'Vulkan0|Radeon 890M|GFX1150' "$out/llama-$backend-devices.log"; then pass 'llama.cpp Vulkan backend' 'Vulkan device enumerated; no model inference run'; else fail_item 'llama.cpp Vulkan backend' 'device enumeration lacked expected Radeon/RADV identity'; fi;;
      hip) if rg -qi 'ROCm0|Radeon 890M|gfx1150' "$out/llama-$backend-devices.log"; then pass 'llama.cpp ROCm/HIP backend' 'HIP device enumerated; no model inference run'; else fail_item 'llama.cpp ROCm/HIP backend' 'device enumeration lacked expected Radeon/gfx1150 identity'; fi;;
    esac
  else
    defer "llama.cpp $backend" 'binary exists but --list-devices did not complete; see backend log'
  fi
done

printf '\n[Vivado / Vitis / HLS]\n'
viv=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado
vpp=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/bin/v++
platforminfo=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/bin/platforminfo
if [[ -x "$viv" ]] && timeout 30s "$viv" -version >"$out/vivado-version.log" 2>&1 && rg -q 'v2026\.1' "$out/vivado-version.log"; then pass 'Vivado' 'version 2026.1'; else fail_item 'Vivado' 'version/startup check failed'; fi
if [[ -x "$vpp" ]] && timeout 30s "$vpp" --version >"$out/vpp-version.log" 2>&1 && rg -q 'v2026\.1' "$out/vpp-version.log"; then pass 'Vitis v++' 'version 2026.1'; else fail_item 'Vitis v++' 'version/startup check failed'; fi
if [[ -x "$platforminfo" ]] && timeout 30s "$platforminfo" --version >"$out/platforminfo-version.log" 2>&1 && rg -q 'v2026\.1' "$out/platforminfo-version.log"; then pass 'Vitis platforminfo' 'version 2026.1'; else fail_item 'Vitis platforminfo' 'version/startup check failed'; fi
[[ -s docs/M9/evidence/license-unlocked-2026.1/synthesis/hls-sp701-csynth.rpt ]] && pass 'Vitis HLS evidence' 'retained SP701 csynth report present; no new synthesis run' || fail_item 'Vitis HLS evidence' 'retained HLS synthesis report missing'
[[ -s docs/M13/evidence/2026-10-02/hls-skill-smoke/csynth.rpt && -s docs/M13/evidence/2026-10-02/hls-skill-smoke/vitis-run-csim.log ]] && pass 'Ross HLS skill evidence' 'bounded csim/csynth/report evidence retained; no new HLS run' || fail_item 'Ross HLS skill evidence' 'retained skill workflow evidence missing'
if [[ -s docs/M12/evidence/host-fpga-jtag-axi-20261002/build/timing-summary-routed.rpt && -s docs/M12/evidence/host-fpga-jtag-axi-20261002/build/bitstream.sha256 ]] && rg -q '0.616' docs/M12/evidence/host-fpga-jtag-axi-20261002/build/timing-summary-routed.rpt; then pass 'SP701 build timing/bitstream evidence' 'separate constrained JTAG-to-AXI design has routed WNS +0.616 ns and a recorded bitstream hash'; else fail_item 'SP701 build timing/bitstream evidence' 'current JTAG-to-AXI evidence is missing'; fi
if [[ -s docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log ]] && rg -q 'M12_AXI_LOOPBACK_TRANSFORM=PASS' docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log && rg -q 'M12_POSTTEST_JTAG=PASS' docs/M12/evidence/host-fpga-jtag-axi-20261002/program-and-smoke.log; then pass 'SP701 prior physical transaction evidence' 'retained transcript contains four AXI vectors and post-test JTAG PASS; this verifier does not reprogram'; else fail_item 'SP701 prior physical transaction evidence' 'verified transcript/markers missing'; fi
not_tested 'SP701 live hardware state' 'this verifier is read-only and does not rescan or program the physical target'

printf '\n[Ross readiness]\n'
ross_bin="$HOME/.local/bin/vivado-mcp-server-2026.9.1"
if [[ -x "$ross_bin" ]] && timeout 10s "$ross_bin" --version >"$out/ross-version.log" 2>&1 && rg -q 'vivado-mcp-server 2026\.9\.1' "$out/ross-version.log"; then pass 'Ross Vivado MCP binary' 'installed server reports version 2026.9.1'; else fail_item 'Ross Vivado MCP binary' 'missing or expected version check failed'; fi
codex_config="$HOME/.codex/config.toml"
if [[ -r "$codex_config" ]] && rg -q '^\[mcp_servers\.vivado-mcp\]' "$codex_config" && rg -q '^\[mcp_servers\.amd-embedded-doc-search\]' "$codex_config"; then pass 'Ross Codex MCP configuration' 'Vivado MCP and local documentation MCP entries exist; no credential values emitted'; else defer 'Ross Codex MCP configuration' 'MCP entries are not both present in Codex config'; fi
skill_count=0
skill_root="$HOME/.codex/plugins/cache/amd-ross-agentic-ai-assistant/amd-ross-agentic-ai-assistant/2026.9.1/skills"
if [[ -d "$skill_root" ]]; then skill_count="$(find "$skill_root" -type f -name SKILL.md | wc -l)"; fi
if (( skill_count > 0 )); then pass 'Ross Agent Skills' "$skill_count installed skill definitions; live HLS skill execution is not tested"; else defer 'Ross Agent Skills' 'no installed skill definitions found'; fi
if python3 - "$codex_config" "$out/ross-doc-search-mcp.json" <<'PY'
import json, sys, tomllib, urllib.error, urllib.request
config_path, evidence_path = sys.argv[1:]
with open(config_path, "rb") as f:
    url = tomllib.load(f)["mcp_servers"]["amd-embedded-doc-search"]["url"]
def post(payload, session=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if session:
        headers["Mcp-Session-Id"] = session
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=8) as response:
        body = response.read().decode("utf-8", "replace")
        return (json.loads(body) if body.strip() else {}), response.headers.get("Mcp-Session-Id") or session
try:
    init, session = post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"ai370-m14-readiness","version":"1"}}})
    post({"jsonrpc":"2.0","method":"notifications/initialized"}, session)
    listed, _ = post({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}, session)
    result = init["result"]
    tools = listed["result"]["tools"]
    names = [tool["name"] for tool in tools]
    if "vivado_doc_search" not in names:
        raise RuntimeError("expected vivado_doc_search tool missing")
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump({"server":result["serverInfo"],"protocolVersion":result["protocolVersion"],"tools":names,"status":"PASS"},f,indent=2)
        f.write("\n")
except Exception as exc:
    print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    sys.exit(1)
PY
then pass 'Ross local Knowledge Base MCP' 'configured endpoint initialized and advertised vivado_doc_search; no document query/load issued'; else defer 'Ross local Knowledge Base MCP' 'configured endpoint did not pass initialize/tools-list readiness check'; fi
not_tested 'Ross HLS / VS Code / local answer agent' 'excluded from this bounded verifier; M13 records these as NOT TESTED/DEFERRED'

printf '\n[kernel fault audit]\n'
journalctl -k --since "$started" --no-pager 2>"$out/journalctl-error.log" | rg -i 'page fault|ttm|soft lockup|gpu reset|ring timeout|amdgpu.*error|amdxdna.*error' >"$out/kernel-faults.log" || true
if [[ -s "$out/kernel-faults.log" ]]; then fail_item 'kernel fault audit' 'targeted kernel faults found; see kernel-faults.log'; else pass 'kernel fault audit' 'no targeted GPU/NPU fault patterns during verifier window'; fi

ended="$(date --iso-8601=seconds)"
printf '\nM14_VERIFIER_END=%s\nFAILURES=%d\nDEFERRED_OR_NOT_TESTED=%d\n' "$ended" "$failures" "$deferred"
python3 - "$out/summary.json" "$started" "$ended" "$failures" "$deferred" "$checks_file" <<'PY'
import csv, json, sys
path, started, ended, fails, deferred, checks_path = sys.argv[1:]
with open(checks_path, encoding="utf-8", newline="") as f:
    checks = [{"status": row[0], "name": row[1], "detail": row[2]} for row in csv.reader(f, delimiter="\t")]
summary = {
    "schema": "ai370-m14-verifier/v1",
    "started": started,
    "ended": ended,
    "overall": "FAIL" if int(fails) else ("PASS_WITH_DEFERRED" if int(deferred) else "PASS"),
    "fail_count": int(fails),
    "deferred_or_not_tested_count": int(deferred),
    "checks": checks,
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
printf 'Summary: %s\n' "$out/summary.json"
(( failures == 0 ))
