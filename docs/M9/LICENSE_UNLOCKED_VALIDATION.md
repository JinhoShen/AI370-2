# M9 license-unlocked toolchain validation — PASS

Date: 2026-10-01 (Asia/Taipei). This addendum continues from `a2c335b`. It preserves the previous license-blocked evidence and the original M9.0/M9.1, decision, and checkpoint history. Host: Ubuntu 24.04.4 LTS. This is actual native installation validation; it does not claim that Ubuntu 24.04.4 is an officially supported 2026.1 host.

## License and tool startup

Vivado 2026.1 reports: “A valid Vivado Design Suite ENTERPRISE license has been detected”; the license is active and reports permanent expiry. The source is the local user license file at `/home/shen/.Xilinx/Xilinx_shen.lic`. License contents, keys, and hashes are intentionally excluded from this repository. No license environment-variable names were set in the verification shell. Vitis and the separate Vitis Embedded installation both start and report v2026.1; Vitis HLS v2026.1 also started and completed synthesis. See `evidence/native-2026.1/logs/*license*version.log` and the Vivado/HLS run logs.

| Tool / test | Result | Evidence |
|---|---|---|
| `vivado -version` | PASS — v2026.1, build 6511674 | `evidence/native-2026.1/logs/vivado-license-version.log` |
| Vivado batch/Tcl | PASS — active Enterprise license; Tcl completed with exit 0 | `evidence/native-2026.1/logs/vivado-sp701-smoke-console.log`, `.rc` |
| SP701 board / device recognition | PASS — `xilinx.com:sp701:part0:1.0`, `xc7s100fgga676-2` | Same Vivado log; the Spartan-7 device module Add is in `evidence/native-2026.1/logs/add-spartan7-support.log` |
| SP701 RTL project / synthesis | PASS — `m9_adder`, 0 synthesis errors; exit 0 | Vivado log and `evidence/license-unlocked-2026.1/synthesis/vivado-sp701-utilization.rpt` |
| Vivado utilization | PASS — SP701 report generated; 4 Slice LUTs and 5 Slice Registers used | Utilization report above |
| Digilent board recognition | PASS — Arty A7-35 resolves to `digilentinc.com:arty-a7-35:part0:1.0`; its `xc7a35ticsg324-1L` part and RTL synthesis also passed | `evidence/native-2026.1/logs/vivado-license-smoke-console.log`, `.rc` |
| Vitis HLS 2026.1 C synthesis on SP701 | PASS — `m9_adder`, Spartan-7 target `xc7s100-fgga676-2`; exit 0 | `evidence/native-2026.1/logs/hls-license-smoke-console.log`, `.rc`; `evidence/license-unlocked-2026.1/synthesis/hls-sp701-csynth.rpt` |
| Vitis / Vitis Embedded startup | PASS — both report v2026.1; the earlier GUI startup evidence remains valid | `evidence/native-2026.1/logs/vitis-license-version.log`, `vitis-embedded-license-version.log`, and prior GUI startup logs |
| Vitis Embedded platform enumeration | PASS — eight 2026.1 `.xpfm` platforms enumerated; each was parsed individually in the retained platform report | `evidence/license-unlocked-2026.1/logs/embedded-platform-list.json`; prior `evidence/acceleration-2026.1/logs/platforminfo-individual.txt` |
| AMD/Xilinx Board Store | PASS — Vivado recognizes SP701, and installed SP701 `board.xml` SHA-256 matches the local Board Store source | Vivado log; source/install comparison recorded below |
| JTAG hardware enumeration | DEFERRED — Vivado Hardware Manager found no target; no Xilinx/Digilent cable appears in the captured USB list | `evidence/license-unlocked-2026.1/logs/hw-target-probe.log`, `lsusb-at-hw-probe.txt` |

The registered installer maintenance `Add` action installed only the previously missing `Spartan-7 FPGAs` device module. The configuration selected no other modules. It completed successfully without reinstalling Vivado, Vitis, HLS, or Acceleration. The selected module was then proven usable by Vivado part lookup and synthesis and HLS part lookup and synthesis.

The SP701 `board.xml` at the local Board Store source and the installed Vivado repository have the same SHA-256: `c84db52788cbfdfe4664e23f7b2045c276bfa17e7a4849bb48025876776d8091`. Digilent recognition is proven separately by the Arty A7-35 board-part query. Vitis `platforminfo -l` returned eight embedded platforms; individual parse evidence is retained from the earlier M9 acceleration validation. Enumeration and metadata parsing do not claim implementation on those platforms or FPGA execution.

## Protected-stack regression after synthesis and device-support Add

| Regression | Result | Evidence |
|---|---|---|
| HIP | PASS — Radeon 890M `gfx1150`, 1,024 GPU results | `evidence/license-unlocked-2026.1/logs/hip-regression.log`, `.rc` |
| Vulkan baseline | PASS — Radeon 890M / RADV GFX1150, 1,024 shader results; CPU fallback forbidden | `evidence/license-unlocked-2026.1/logs/vulkan-regression.log`, `.rc` |
| XRT / NPU enumeration | PASS — XRT 2.21.75; Strix NPU at `0000:c6:00.1`; amdxdna `2.21.260102.53.release`; firmware 1.1.2.64 | `evidence/license-unlocked-2026.1/logs/xrt-npu-examine.log`, `.rc` |
| M5 NPU CNN | PASS — 10 iterations, CPU fallback disabled, all profiled nodes on VitisAI, NPU counter +14,621,103 ns, max CPU-reference error 0.0 | `evidence/license-unlocked-2026.1/npu-regression.json`, `logs/npu-cnn-regression.log`, and retained profile under `output/M9/license-npu-run/` |
| New kernel errors during GPU/NPU regressions | None in captured test windows | `evidence/license-unlocked-2026.1/logs/kernel-*-regression-window.log` (`-- No entries --`) |

The Qwen Q8 Vulkan failure from the preceding commit was not rerun. No Kernel, Mesa/RADV, libdrm, ROCm, system XRT, amdxdna, or firmware package was changed in this M9 continuation. Exact currently observed protected-stack versions and the license status summary are in `evidence/license-unlocked-2026.1/logs/license-and-protected-stack.txt`.

## Scope result

**M9 software toolchain validation: PASS. FPGA TOOLCHAIN WORKING STATE established.** Vivado batch/Tcl, licensed SP701 RTL synthesis, HLS C synthesis, tool startup, board/device recognition, installed-platform parsing, and HIP/Vulkan/XRT/NPU/M5 regressions passed. The previous license-blocked runs remain preserved as historical evidence in `NATIVE_INSTALL_RESULT.md` and their original logs.

Physical JTAG detection, bitstream implementation/programming, and live FPGA execution remain **DEFERRED** because Hardware Manager found no connected target. They do not block this software-toolchain scope. No hardware PASS is claimed. The host OS compatibility caveat remains: native success is demonstrated, official support is not asserted.

Vivado also emitted board-file parse warnings for unrelated legacy Avnet, alinx, and AlphaData XML files in the broad installed repository. The selected SP701 and Digilent Arty definitions were recognized, their target parts loaded, and the tested synthesis runs completed with zero synthesis errors; the unrelated repository warnings are retained in the full logs and are not counted as target-board verification failures.
