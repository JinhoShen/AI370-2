# AI370-2 rebuild guide

This guide is the construction plan for a **new, compatible workstation** using Ubuntu, T7 deployment resources, the AI370-2 GitHub repository and Codex. It is not a machine image or a claim that old PASS results transfer to new hardware.

**Rebuild rule:** begin again at M0 and re-verify M0 through M15. Prior AI370-2 results are `KNOWN GOOD CONFIGURATION`, `KNOWN ISSUE`, `REFERENCE` or historical evidence only. Every new host must produce its own inventory, logs, exact versions and evidence. A result is PASS only for the workload actually executed on that host.

## A. Project objective and source of truth

Build and validate an AMD Ryzen AI workstation with its specific Radeon GPU and XDNA2 NPU, plus the chosen AMD/Xilinx FPGA workflow. Maintain a clean, reviewable build history and a guarded recovery path.

- GitHub `JinhoShen/AI370-2` is the primary knowledge source: committed scripts, build decisions, evidence, known issues and milestone status.
- T7 is deployment/migration/offline resource media: large installers, selected packages, chosen models, manifests and a Git bundle fallback.
- Codex follows this guide and the current `docs/ROADMAP.md`, inspects the target host, then advances one evidence-gated milestone at a time.
- Never copy the old machine's full root filesystem, installed Xilinx tree, Python venv, caches or build outputs to claim a rebuild.
- Keep `ACTUAL`, `VERIFIED`, `PASS`, `FAIL`, `BLOCKED`, `DEFERRED`, `UNKNOWN`, `OPEN` and `PLAN` distinct. Preserve old failure records.

## B. Hardware discovery (M0)

Before installation, record motherboard/system model, BIOS/UEFI, CPU, memory capacity/speed, storage/device identifiers, PCI IDs, USB inventory, GPU model/PCI ID, NPU model/PCI ID and any FPGA board/cable/target. Capture exact command output and timestamps. Treat AI370-2's HX 370 / Radeon 890M (`gfx1150`) / XDNA2 configuration as a reference; a new machine may differ. Identify Secure Boot state and available disk space before DKMS, firmware or large tool installation.

Start with read-only inventory. Do not infer device identity from a marketing product name alone. Record deviations from the reference configuration before deciding compatibility gates.

## C. Ubuntu baseline and support decision (M1)

Record the exact Ubuntu point release, kernel, repositories, firmware, filesystem and current package versions. The original host ran Ubuntu 24.04.4 LTS and successfully ran the native AMD/Xilinx 2026.1 tools, but the local official-support review did not confirm Ubuntu 24.04.4 as supported; official matrix evidence identified Ubuntu 24.04.3 as the listed point release. **Native installation success is not official support.** On a new host, check the current vendor support matrix and preserve the source/date; if the chosen OS is outside confirmed support, record the explicit compatibility decision and validate empirically.

The ISO presently inventoried on T7 is Ubuntu 24.04.1, not an exact 24.04.4 image. Do not silently label it an exact reconstruction medium.

## D. Protected-stack policy and golden reference

Before changing anything, record kernel, Mesa/RADV, libdrm, ROCm/HIP/HSA, XRT, amdxdna DKMS, NPU firmware, GPU/NPU device enumeration, package holds and boot configuration. Save a recovery checkpoint appropriate to the change and a package transaction simulation.

Old-host known-good reference (not a requirement to force onto different hardware): Linux 6.17.0-14, Mesa 25.2.8, libdrm 2.4.125, ROCm 7.2.1 / HIP 7.2.53211, system XRT 2.21.75, amdxdna `2.21.260102.53.release_20260309`, NPU firmware 1.1.2.64. Re-identify the exact compatible release for each new target. Never blindly upgrade/downgrade or replace these families; use APT simulation and a protected-stack guard. If a necessary install changes a protected component, stop at a compatibility gate and document alternatives.

## E. ROCm / HIP (M3)

Use the target GPU's supported ROCm release and an isolated/pinned userspace where appropriate. Avoid broad distribution upgrades. Verify `rocminfo`, `hipconfig`, compiler/runtime versions, actual GPU device (`gfx*`) and a numeric HIP compute test whose CPU fallback is impossible. Save source, build command, output, exit code, device identity, package diff and kernel fault window. PASS requires correct GPU-produced results and no fallback; enumeration alone is readiness, not compute PASS.

## F. Vulkan / Mesa / RADV (M4)

Inventory Vulkan ICDs and the selected physical device with `vulkaninfo`; explicitly select the intended Radeon/RADV device. Run the versioned compute/shader regression and validate result values, device identity and no software/CPU fallback. Protect Mesa, RADV and libdrm once validated. If kernel logs show device loss, page faults, TTM corruption, reset, ring timeout or lockup, stop GPU workloads and preserve the exact test/logs. Do not mask driver errors or turn an unrelated smaller regression into a resolution claim.

## G. XDNA2 / XRT / Ryzen AI / NPU (M5, M8)

Treat kernel driver, DKMS package, system XRT, plugin, firmware and userspace SDK as one compatibility set. Capture package, module and firmware versions/checksums before and after. Use an isolated Python environment for SDK dependencies; do not install a plugin package if its maintainer scripts would replace the protected driver or XRT without an approved gate.

For ONNX NPU PASS, disable CPU execution-provider fallback, disable ORT fallback, profile every executed node, prove a live NPU device descriptor and positive NPU hardware-time delta, and compare output against an independent CPU reference. A CPU EP being registered is not itself fallback; actual node assignment/execution is the criterion. If the graph requires CPU nodes under strict policy, record NOT SUPPORTED/NOT RUN rather than pass.

M8 reference scope was ONNX workload PASS; NPU LLM remained DEFERRED. GGUF on CPU/GPU does not imply NPU use.

## H. Local AI / llama.cpp / Lemonade (M6, M7, M7.1)

Build llama.cpp from a recorded source revision with distinct CPU, Vulkan and ROCm configurations. Verify executable version, backend list and device list separately. For each inference, explicitly select one backend/device and preserve logs proving allocation/execution; never report an unproven fallback as backend PASS. Begin with small context, few output tokens, low layer offload, bounded memory and swap disabled. Audit kernel logs after each GPU attempt.

M7 on the original host passed only its conservative bounded benchmark scope, not high-load or long-duration stability. M7.1 remains OPEN: Qwen3.6-35B-A3B Q8 Vulkan previously caused command-submission memory errors and Vulkan device loss. Do not rerun that known GPU case casually; follow the committed safety gate. The newer Qwen3.8 model smokes are bounded M7 evidence, not a stability claim. NPU inference of GGUF models is not established.

Use `docs/deployment/AI370-2_WORKSTATION_SNAPSHOT_INVENTORY.md` for model locations and existing integrity/test evidence. Models are selected optional resources, not a base rebuild dependency. Preserve only selected models in a future kit; do not make duplicate cache copies part of the install procedure.

## I. Vivado / Vitis / HLS (M9, M10)

Use the original Vivado/Vitis 2026.1 installer TAR and its recorded SHA256 at `AMD_AI_Workstation/01_System_Resources/AMD_Xilinx/2026.1/`. T7 was remounted and the installer hash was verified against the manifest on 2026-10-06. Do not copy `/home/shen/tools/Xilinx/2026.1` or re-use extracted installer trees. Select Vivado, Vitis Embedded, Vitis HLS, required device families, and only the needed Acceleration components. Confirm installed device/board/platform support through tool queries, not installer checkboxes alone.

Before adding prerequisites, inspect vendor `installLibs.sh` but do not blindly run a broad superseding package list. Simulate APT, inspect every protected graphics/ROCm/XRT/driver change, install only actual missing libraries, and never use fake ABI symlinks (e.g. ncurses/tinfo major versions). Verify `vivado -version`, Tcl batch startup, RTL synthesis, `vitis -v`, `vitis_hls -version`, HLS C synthesis/report, `v++` and platform enumeration. A valid license is separate from installation; keep license data outside Git and T7 manifests.

On the old host, native 24.04.4 installation and software tests passed while official support remained unconfirmed. That outcome does not transfer to another Ubuntu point release or machine.

## J. SP701 / cable driver / JTAG (M11)

For the SP701, identify board part `xilinx.com:sp701:part0:1.0`, FPGA `xc7s100fgga676-2`, FT4232H USB functions and live JTAG target before design changes. Use Vivado 2026.1's bundled `install_drivers` only when missing and applicable; inspect its output and udev rules. Verify `hw_server`, Hardware Manager target/device/PART/IDCODE/DNA before programming. Do not alter device tree or install third-party cable drivers by guesswork.

On the old host, SW13 was set to JTAG mode, cable driver installed, and readonly identity (IDCODE `0x037C7093`) was verified. A new target still requires fresh detection. Never program during discovery-only stages.

## K. SP701 DDR validation

Use the installed official SP701 board definition, `ddr3_sdram_preset`, MIG 7-series, official `mig.prj`, and generated MIG constraints. Never guess DDR pins, IOSTANDARD, clocks or timings. Preserve the distinction between the physical 1 GiB Micron DDR3 SODIMM and the reference MIG's configured 512 MiB address range; AXI data width 64 is not the physical DDR bus width (16-bit).

Before programming, require synthesis/implementation/route PASS, zero blocking DRC, valid timing, generated bitstream and traceable official constraints. Then separately verify calibration, physical write/read/compare and error indication via MIG traffic/ILA. The prior SP701 test passed only its bounded 16 MiB range for a 30-second run; it did not exhaustively test 512 MiB or the full 1 GiB module. Keep these boundaries in the report.

## L. Host ↔ FPGA architecture

Do not assume the SP701 is a PCIe accelerator or has a ready `.xpfm`/XRT card runtime. The verified path on the reference system was Vivado Hardware Manager over FT4232H JTAG to `jtag_axi` v1.2 and an AXI-Lite register, with four physical host write/read vectors. This is a development/control/data round-trip, not application-facing XRT execution or a high-throughput data plane. System XRT 2.21.75 is protected for Ryzen AI/NPU; do not replace it to force Alveo-style host APIs onto SP701.

For a new board, establish the supported transport architecture from installed design data and evidence first. Keep XRT host API, xclbin execution, sustained data-plane throughput and GPU/NPU-to-FPGA AI workload DEFERRED until actually built and tested.

## M. Ross Agentic AI / Local KB / Skills / Vivado MCP (M13)

Use AMD-provided artifacts and versions recorded in M13 evidence; keep downloaded installers/archives on T7 only when required for offline rebuild. Keep account/license secrets outside Git. Check the local KB container/image/snapshot, model, Skills and MCP requirements before assuming it is portable. Reconfigure machine-local endpoint/container addresses after migration.

Reference-host evidence: AMD Vivado MCP startup/discovery, Codex CLI document search, Vivado 2026.1 read-only part/version queries, 49 installed Skills, local KB retrieval, and a bounded HLS Skill synthesis/report workflow passed. Ross materially informed the M12 JTAG-to-AXI design. Qwen3.8 Q4_K_XL authored the bounded AXI-Lite RTL change; XSim and licensed Vivado synthesis passed through the supervised Codex sandbox flow. Vivado license checkout requires host network access for that invocation because FlexNet is locked to a host NIC/MAC hidden by the sandbox network namespace. Direct custom local-provider tool protocol, end-to-end local tool autonomy/air-gap, full Vitis IDE assistant and autonomous MCP hardware programming remain unverified. Do not assume an existing Qwen GGUF works as Ross's answer model.

## N. Unified final validation (M15)

Only after subsystem work stabilizes, capture one timestamped, guarded final run covering platform inventory, HIP, Vulkan, XRT/NPU enumeration, strict NPU CNN, selected bounded Local AI model, Vivado/Vitis/HLS/v++, FPGA software artifacts, Ross readiness, automation and targeted kernel audit. Include board hardware tests only when physically available and safe. Recheck exact protected versions and evidence integrity. Keep OPEN/DEFERRED items visible; do not force an overall PASS by omitting a failing known issue.

The reference host remains PRE-FINAL/PASS_WITH_DEFERRED: M7.1 is OPEN, M8 NPU LLM is DEFERRED, M12 XRT application integration remains DEFERRED, M13 bounded local-Qwen RTL editing and supervised XSim/Vivado synthesis are verified while direct provider-tool protocol and air-gap remain DEFERRED, and M14 rebuild automation is incomplete. T7 current bundle and listed payload checksums are verified, but complete offline dependency closure/clean rebuild and the sudoers syntax audit remain open. A new host requires its own final evidence and status review.

## O. Deployment / migration sequence

1. Clone current `main` from GitHub. If offline, verify and test-clone the commit-addressed bundle under `AMD_AI_Workstation/02_Deployment/AI370-2/Git/`, compare clone HEAD to `MASTER_MANIFEST.md`, and reconcile with GitHub when online. The 2026-10-06 bundle matched the then-current local `main`; earlier bundles are historical and must not be treated as current.
2. Inventory hardware and Ubuntu; decide support/compatibility gates and storage capacity.
3. Read this guide, `docs/ROADMAP.md`, platform records and the relevant milestone result/evidence before each milestone.
4. Select T7 resources from `T7_MANIFEST.md` and verify exact size/SHA256 before use. The active root is `AMD_AI_Workstation/` with `01_System_Resources/`, `02_Deployment/AI370-2/`, and `03_AI_Models/`. The current Ubuntu ISO is 24.04.1, not 24.04.4. The 2026.1 Xilinx TAR, selected Ryzen AI/XRT/XDNA/firmware and ROCm packages are inventoried, but they do not constitute a complete offline dependency closure.
5. Rebuild M0→M15 using scripts only within their documented scope. Create host-local venvs and build trees; never import them from the old machine snapshot.
6. Write new-host evidence under a host/date-specific directory; preserve original repository history and old machine evidence.
7. Keep a separate secrets procedure: restore the license/account configuration from its authorized source, never record secret values in Git or `SHA256SUMS`.

T7 is deployment/migration/offline resource media, not a current-machine image. Do not include extracted installers, installed Xilinx trees, caches, build output or venvs in the deployment kit unless a demonstrated offline/rebuild limitation justifies a specific exception. The T7 `照片` directory is unrelated user data and must not be touched by AI370-2 workflows.

## P. Known issues and lessons

- Ubuntu 24.04.4 native Xilinx 2026.1 success did not establish official support; prior official review confirmed 24.04.3 in the support matrix and did not confirm 24.04.4.
- A broad vendor prerequisite transaction risked replacing/upgrading protected Mesa/ROCm/XRT dependencies. Use simulation and actual-error-driven installation; do not replay `installLibs.sh` wholesale.
- Do not create ABI symlinks to impersonate `libtinfo5`/`libncurses5`.
- Preserve M5 XDNA2 known-good versions as a matched stack. A kernel-module signature warning with Secure Boot disabled and the specified DKMS driver loaded was a verifier false negative, not a compute failure; policy must record WARNING only when functional checks pass.
- NPU PASS requires strict no-fallback execution evidence, NPU counter activity and independent output comparison.
- Qwen3.6 Q8 Vulkan device loss remains M7.1 OPEN; do not replay a known device-lost case absent an explicit safe diagnostic plan.
- SP701 required SW13 JTAG mode, Vivado cable driver/udev readiness and FT4232H target checks. USB detection alone is not JTAG/FPGA identity.
- SP701 DDR PASS was bounded; 16 MiB / 30 seconds is not exhaustive full-device coverage.
- SP701 JTAG-to-AXI is a real physical development path but does not make the board a standard PCIe XRT accelerator.
- Ross Local KB/Skills/Vivado MCP provided practical documentation/HLS support and influenced M12 architecture, but local retrieval is not the same as a complete air-gapped agent.
- Use APT guard + simulations, recovery checkpoint, exact before/after protected stack records, preserved raw evidence and explicit rollback conditions. Do not roll back based on a policy false negative.
- Preserve FAIL/BLOCKED/DEFERRED/OPEN history. Missing evidence is UNKNOWN/NOT TESTED, never PASS.

## Q. Reference verification commands

Use the current script help and milestone documentation before running; scripts may have system-specific prerequisites and some are intentionally workload-bearing.

```bash
cd /home/<user>/AI370-2
git status --short
git rev-parse HEAD
git diff --check
./scripts/verify_m14_workstation.sh
./scripts/verify_m14_evidence.sh
./scripts/apt_change_guard.py --help
```

The workstation verifier executes bounded accelerator checks; it is not a read-only inventory. On a new host, inspect its scope and safety conditions before execution, and run only after the relevant milestone authorizes those tests. M5 CNN strict no-fallback evidence is produced by `verify/npu_cnn.py`; model-specific checks are documented in M7/M15. Vivado DDR and JTAG-to-AXI Tcl sources are under `projects/FPGA/` and their reports under `docs/M11` / `docs/M12`.

## R. Recovery and rollback policy

Before any protected-stack or boot-sensitive action: inventory versions; preserve a recoverable checkpoint suitable for that failure mode; simulate package changes; capture package/module/firmware checksums; define an objective rollback trigger and tested recovery commands. For DKMS or firmware work, plan reboot and console recovery before acting. Never restore a historical CP0 archive as if it were a current-state image.

If any gate fails, stop the dependent step, preserve exact commands/logs/status/exit code, restore only from the matching validated checkpoint when necessary, then rerun the relevant verification. Do not hide a failed first attempt after a successful retry. If recovery media, firmware, license, board, or supported OS information is missing, mark the subtask BLOCKED/DEFERRED and proceed only with independent safe work.
