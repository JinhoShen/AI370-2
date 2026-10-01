#!/usr/bin/env bash
set -euo pipefail

repo=/home/shen/AI370-2
backend=${1:?usage: run_llama_server_smoke_m6.sh cpu|vulkan|hip}
model=$repo/resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf
root=$repo/output/M6
case "$backend" in
  cpu) bin=$root/build-cpu/bin/llama-server; device=none; layers=0; port=18980 ;;
  vulkan) bin=$root/build-vulkan/bin/llama-server; device=Vulkan0; layers=1; port=18981 ;;
  hip) bin=$root/build-hip/bin/llama-server; device=ROCm0; layers=1; port=18982 ;;
  *) echo "unsupported backend: $backend" >&2; exit 2 ;;
esac
log=$root/$backend-server-smoke.txt
response=$root/$backend-server-response.json

if [[ ${M6_IN_SCOPE:-0} != 1 ]]; then
  exec systemd-run --user --scope --quiet -p MemoryMax=24G -p MemorySwapMax=0 -p CPUQuota=800% \
    -- /usr/bin/timeout --signal=TERM --kill-after=10s 240s env M6_IN_SCOPE=1 "$0" "$backend"
fi

started=$(date --iso-8601=seconds)
if python3 - "$port" <<'PY' >/dev/null 2>&1
import socket, sys
with socket.socket() as s:
    s.bind(("127.0.0.1", int(sys.argv[1])))
PY
then :; else echo "localhost port $port is already occupied" >&2; exit 1; fi
"$bin" --model "$model" --host 127.0.0.1 \
  --port "$port" --ctx-size 128 --batch-size 16 --ubatch-size 8 --threads 8 \
  --threads-batch 8 --device "$device" --gpu-layers "$layers" --reasoning off --verbose \
  > "$log" 2>&1 &
server_pid=$!
cleanup() {
  kill -INT "$server_pid" 2>/dev/null || true
  for _ in $(seq 1 50); do kill -0 "$server_pid" 2>/dev/null || break; sleep 0.1; done
  kill -KILL "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for _ in $(seq 1 60); do
  if python3 - "$port" <<'PY' >/dev/null 2>&1
import sys, urllib.request
urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=2).read()
PY
  then
    ready=1
    break
  fi
  kill -0 "$server_pid" 2>/dev/null || { echo 'llama-server exited before readiness' >&2; exit 1; }
  sleep 1
done
[[ $ready == 1 ]] || { echo 'llama-server readiness timed out' >&2; exit 1; }

python3 - "$response" "$backend" "$port" <<'PY'
import json, sys, urllib.request
from pathlib import Path
target, backend, port=sys.argv[1:]
expected=f"M6_SERVER_{sys.argv[2].upper()}_OK"
payload=json.dumps({"model":"local","messages":[{"role":"user","content":f"Reply with exactly {expected} and no other text."}],"max_tokens":32,"temperature":0,"stream":False}).encode()
request=urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=payload,headers={"Content-Type":"application/json"})
with urllib.request.urlopen(request,timeout=60) as response:
    result=json.load(response)
Path(target).write_text(json.dumps(result,indent=2)+"\n")
text=result["choices"][0]["message"]["content"].strip()
print(json.dumps({"expected":expected,"response":text,"usage":result.get("usage")},ensure_ascii=False))
if text != expected:
    raise SystemExit(f"response was not exactly {expected!r}")
PY

cleanup
trap - EXIT
journalctl -k -b --since "$started" --no-pager > "$root/$backend-server-kernel.txt"
echo "PASS: llama-server $backend API inference, response marker and process cleanup"
