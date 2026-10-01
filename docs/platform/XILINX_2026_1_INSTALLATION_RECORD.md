# AMD/Xilinx 2026.1 Installation Record — AI370-2

**Record date:** 2026-10-01 (Asia/Taipei)
**State basis:** actual installation files, installer records, M9/M10 logs and Git history, supplemented by a fresh read-only host inventory. “VERIFIED” means the named software query or test passed; it does not imply hardware execution beyond that test.

## Official AMD/Xilinx 2026.1 guidance

| Topic | Official 2026.1 source says | AI370-2 comparison |
|---|---|---|
| OS support | UG973 lists Ubuntu 22.04.3/.4/.5 and 24.04, .1, .2, .3 (64-bit); it also notes Ubuntu needs `libtinfo.so.5`. | Host is Ubuntu 24.04.4. UG973 list does not enumerate .4, so official support for this exact point release is **not established**. Native installation and tested operations succeeded locally; this is not an official-support claim. [UG973 OS matrix](https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Supported-Operating-Systems) |
| Vitis OS and resource requirements | UG1742 marks Ubuntu 24.04 through 24.04.3 supported for embedded/HLS and acceleration. It lists minimum memory 32 GB (64 GB recommended) for embedded/HLS and 64 GB (80 GB recommended) for acceleration; full Vitis requires 200 GB. For Alveo XRT deployment, tested kernel versions are shown per OS, and Ubuntu HWE is not supported for that deployment. | Current host is 24.04.4 with kernel 6.17.0-14 and 50,103,095,296 physical RAM bytes (~46.65 GiB). It is outside the listed 24.04.x point releases; kernel 6.17.0-14 matches the matrix's 24.04.3 tested-kernel entry but does not extend OS support. RAM is below the stated 64 GB acceleration minimum. [UG1742 requirements](https://docs.amd.com/r/en-US/ug1742-vitis-release-notes/Installation-Requirements) |
| Installer flow | UG973 full image: decompress and run Linux `xsetup`; lightweight installer can download selected products/device families. UG1742 says Vivado/Vitis share installer; full Vitis selects tools/devices and offers `installLibs.sh` after installation. | Installed from locally available unified 2026.1 archive (SHA-256 in local inventory) using the registered native installation and Add maintenance flow for later components. `installLibs.sh` was not executed because exact simulations showed broad system updates and legacy package names unavailable; actual missing libraries/tools were handled against observed runtime errors. |
| Product/device selection | UG1742 describes full Vitis including Vivado, `v++`, and AI Engine toolchains; standard design selections include Vitis, Vivado, Vitis HLS and Model Composer. Acceleration requires Devices → “Install devices for Alveo and Edge acceleration platforms.” Device families can be selected in installer. | Actual unified core installation plus separately installed Vitis Embedded; Acceleration device module later added; initial Artix-7/Kria/Zynq UltraScale+ MPSoC selection later supplemented by Spartan-7 only. Xilinx/Digilent board definitions were imported/added and then queried by Vivado. [UG1742 installation](https://docs.amd.com/r/en-US/ug1742-vitis-release-notes/Installing-the-Vitis-Software-Platform) |
| Required libraries | UG973/UG1742 recommend using `installLibs.sh` when required libraries are missing, then manually resolving any packages the script misses. They do not state every package in that script is required for every selected workflow. | Vendor script was inspected but not run. Name-based package simulation failed for `libtinfo5` and `libncurses5`; Ubuntu’s candidate transaction planned 49 upgrades (including Mesa/RADV) and 117 new installs. Per-workflow smoke checks and actual loader errors guided installation without ABI symlinks. See `docs/M9/apt-simulation-vendor-prerequisites.txt`, `apt-simulation-ubuntu24-candidate.txt`, `NATIVE_INSTALL_RESULT.md`. |
| License | UG973 says in 2026.1 Vivado requires a valid license file accessible before launch; it describes `XILINXD_LICENSE_FILE` and license tiers/device-feature distinctions. | Early synthesis attempt was BLOCKED by absent configured license, preserved in initial logs. Later Vivado reported active Enterprise license and RTL/HLS synthesis passed. License path/source status is documented without committing the file, key, or hash. [UG973 licensing/features](https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Supported-Devices-and-Features) |
| XRT | UG1742 lists Vitis 2026.1 XRT build `2.23.244`; its Alveo environment setup sources `/opt/xilinx/xrt/setup.sh`. The docs distinguish acceleration tooling from actual XRT-enabled deployment. | Protected system XRT remains `2.21.75` for XDNA2. Vitis bundled utility reports XRT metadata `2.19.0`; setting `XILINX_XRT=/opt/xilinx/xrt` dispatches to system utility 2.21.75. Acceleration Add did not replace system XRT. FPGA card runtime compatibility remains UNKNOWN because no FPGA card was enumerated. [UG1742 component versions](https://docs.amd.com/r/en-US/ug1742-vitis-release-notes/Software-Component-Versions), [environment setup](https://docs.amd.com/r/en-US/ug1742-vitis-release-notes/Setting-Up-the-Environment-to-Run-the-Vitis-Software-Platform) |

The official matrix makes an important distinction: Ubuntu 24.04.3 is listed; Ubuntu 24.04.4 is not. The locally observed 6.17.0-14 kernel matches UG1742's 24.04.3 tested-kernel row, but that does not prove this 24.04.4 host is supported. **Official support for Ubuntu 24.04.4: UNKNOWN / not established. Native software validation: PASS for the documented tests.**

## Actual installation inventory

| Component | Actual installation / selection | Status |
|---|---|---|
| Unified installer | Local `FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar`; SHA-256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`; registered installer under `/home/shen/tools/Xilinx/2026.1/.xinstall/2026.1` | INSTALLED, hash historically verified; see `docs/M9/M9.0_PRECHECK.md` and `NATIVE_INSTALL_RESULT.md` |
| Vivado | `/home/shen/tools/Xilinx/2026.1/2026.1/Vivado`, v2026.1 build 6511674 | INSTALLED / VERIFIED |
| Vitis Unified / Acceleration | `/home/shen/tools/Xilinx/2026.1/2026.1/Vitis`, v2026.1; acceleration CLI and device components | INSTALLED / CLI VERIFIED |
| Vitis Embedded | `/home/shen/tools/Xilinx/vitis-embedded-2026.1/2026.1/Vitis`, v2026.1 | INSTALLED / startup VERIFIED |
| Vitis HLS | v2026.1 via installed Vitis tooling; unified-tree `vitis-run --mode hls` used for final synthesis | INSTALLED / synthesis VERIFIED |
| Device families | Artix-7, Kria SOM/Starter Kit, Zynq UltraScale+ MPSoC from initial install; later Spartan-7 maintenance Add; Acceleration Add selected Alveo/edge and Versal acceleration device modules | INSTALLED; named targets tested below |
| Spartan-7 / SP701 | Spartan-7 added after initial device lookup gap; SP701 board part recognized and used for RTL/HLS synthesis | INSTALLED / VERIFIED |
| Digilent board resources | Local Digilent board sources installed; Arty A7-35 resolves to board part `digilentinc.com:arty-a7-35:part0:1.0`, part `xc7a35ticsg324-1L` | INSTALLED / recognition VERIFIED |
| Xilinx Board Store | Local Xilinx Board Store content added; SP701 source and installed `board.xml` SHA-256 `c84db52788cbfdfe4664e23f7b2045c276bfa17e7a4849bb48025876776d8091` | INSTALLED / SP701 recognition VERIFIED |
| Embedded base platforms | Eight 2026.1 `.xpfm` files in Vitis `base_platforms` | INSTALLED / list and individual parse VERIFIED; build/execution deferred |
| System XRT | `xrt-base 2.21.75`, `xrt-npu 2.21.75`, `xrt_plugin-amdxdna 2.21` | PRESERVED / NPU enumeration VERIFIED; FPGA runtime UNKNOWN |
| Vitis bundled XRT utility | Bundled `xclbinutil` reports build metadata 2.19.0; wrapper can select system utility when `XILINX_XRT=/opt/xilinx/xrt` | Coexistence selection observed; FPGA runtime compatibility UNKNOWN |
| Optional IP cache, PDM, DocNav | Not selected | NOT INSTALLED / not required by verified scope |

### Platform filenames individually parsed

`kv260_base.xpfm`, `vck190_base.xpfm`, `vek280_base.xpfm`, `vek385_base.xpfm`, `vrk160_base.xpfm`, `xilinx_vck190_base_202610_1.xpfm`, `xilinx_vck190_base_dfx_202610_1.xpfm`, `xilinx_vek280_base_202610_1.xpfm`. Parsing establishes that Vitis can read the metadata; it does not establish implementation, programming or execution on those platforms.

## Installation decisions and engineering reasons

1. **VM recommendation retained, native route selected.** Early M9 planning recommended an Ubuntu 24.04.3 guest because exact 24.04.4 support had not been established. The user explicitly chose native 24.04.4 installation/validation. The original recommendation and precheck remain in their original documents/commits; native success is judged by actual evidence, not treated as official support.
2. **Recovery and protected-stack baseline before install.** PRE-M9-NATIVE checkpoint and baseline record the OS/kernel/graphics/ROCm/XRT/XDNA state. This preserved the validated GPU/NPU Golden State as the key acceptance baseline.
3. **No broad `installLibs.sh` transaction.** Vendor package-name simulation could not resolve libtinfo5/libncurses5; Ubuntu candidate simulation would upgrade 49 packages, including Mesa/RADV. The transaction was not run because it crossed the protected Mesa/ROCm/XRT/platform risk boundary. Later only actual runtime needs were addressed. See the preserved simulations.
4. **No ABI symlink workaround.** `libtinfo5`/`libncurses5` were not fabricated through symlinks to newer ABI libraries. ABI identity cannot be asserted by filename alias; actual tools were launched and tested using shipped/runtime-compatible libraries instead.
5. **Core install then Add.** Unified native toolchain installed first; Vitis Embedded occupies its own path because the installer’s Add configuration did not accept that product against the existing installation. Acceleration was added later using the registered installer. No completed product was reinstalled.
6. **Only Spartan-7 added.** User identified SP701. The first install lacked Spartan-7 device support, so Vivado could not resolve the SP701 device. Maintenance Add selected only the missing Spartan-7 family; then part lookup, board recognition and synthesis demonstrated the required closure without broad reinstall.
7. **System XRT 2.21.75 retained.** It serves the validated Ryzen AI / XDNA2 stack. Installing or replacing it with another host XRT would jeopardize NPU Golden State. Vitis utilities could be used in bundled or explicitly selected system-XRT mode; actual FPGA runtime still awaits a matching physical card/platform validation.
8. **HLS runner uses the unified tree.** The separate Embedded tree’s attempted HLS runner encountered a missing Clang tool path in that tree. Final HLS C-synthesis ran through the Unified 2026.1 Vitis tree where the compiler support tools were present; no symlink shim was introduced.

## Installation and validation history (M9 → M10)

Git dates below are commit metadata. This additive record does not modify prior M9/M10 records or failure logs.

| Date (Taipei) | Commit | Event / result |
|---|---|---|
| Oct 1 10:35 | `68def7a` | Pre-install gate documented the VM recommendation and native compatibility caveat. |
| Oct 1 12:10 | `6470ac3` | M9.0 precheck and M9.1 FPGA resource/device/board/platform/license inventory committed. |
| Oct 1 12:37 | `3ac9936` | Explicit native-install decision, PRE-M9-NATIVE recovery checkpoint, protected-stack baseline and APT simulations recorded; VM history retained. |
| Oct 1 14:20 | `6cdc0c4` | Native 2026.1 Vivado/Vitis/Vitis Embedded/HLS installation completed. Initial synthesis attempt remained BLOCKED by license. |
| Oct 1 16:17 | `f112bc3` | Vitis Acceleration device-support Add completed; CLI/platform/XRT inspection documented. |
| Oct 1 18:17 | `a2c335b` | Separate Qwen3.6 Q8 low-load smoke result committed; its Vulkan failure remains an M7.1 issue. |
| Oct 1 19:01 | `0b8c922` | License available; current Vivado/HLS synthesis passed. Spartan-7-only Add fixed SP701 recognition. SP701 and Arty lookup, RTL synthesis, utilization, HLS synthesis and HIP/Vulkan/XRT/NPU/CNN regressions passed. M9 PASS. |
| Oct 1 19:03 | `1d5f6fa` | `v++`, HLS and eight embedded platform parses passed; M10 PASS. |

Detailed logs and retained failures:

- `docs/M9/M9.0_PRECHECK.md`, `M9.1_FPGA_INVENTORY.md`, `PRECHECK_GATE.md`, `NATIVE_INSTALL_DECISION.md`
- `docs/M9/NATIVE_INSTALL_RESULT.md`, `ACCELERATION_INSTALL_RESULT.md`, `LICENSE_UNLOCKED_VALIDATION.md`
- `docs/M9/apt-simulation-vendor-prerequisites.txt`, `apt-simulation-ubuntu24-candidate.txt`
- `docs/M10/RESULT.md` and `docs/M9/evidence/`, `docs/M10/evidence/`
- Qwen Q8 separate issue: `docs/M7/QWEN36_Q8_SMOKE.md`

## Verified results and explicit deferrals

| Check | State | Evidence / limit |
|---|---|---|
| Vivado version and active license | VERIFIED | v2026.1 build 6511674; active Enterprise license. Only license source/status is recorded; secret contents are excluded. |
| SP701 board/part recognition | VERIFIED | `xilinx.com:sp701:part0:1.0`, `xc7s100fgga676-2`. |
| Digilent Arty A7-35 recognition | VERIFIED | `digilentinc.com:arty-a7-35:part0:1.0`, `xc7a35ticsg324-1L`. |
| Vivado RTL synthesis | PASS | `m9_adder`, exit 0, zero synthesis errors. |
| Utilization | VERIFIED | SP701 synthesis report: 4 Slice LUTs and 5 Slice Registers. |
| Vitis HLS synthesis | PASS | `m9_adder` C synthesis targeting SP701/Spartan-7, exit 0; report and RTL generated. |
| Vitis `v++` | VERIFIED | `v++ --version` reports 2026.1. |
| Eight embedded platforms | VERIFIED | Enumerated and individually parsed; no platform implementation/execution claim. |
| HIP baseline | PASS | 1,024 Radeon 890M / gfx1150 results. |
| Vulkan baseline | PASS | 1,024 Radeon 890M RADV GFX1150 shader results; CPU fallback forbidden. This was the baseline test, not Qwen Q8. |
| XRT/NPU | PASS | Strix NPU enumeration, XRT 2.21.75, firmware 1.1.2.64. |
| M5 CNN | PASS | 10 iterations, VitisAI-only, no CPU fallback, NPU counter increased, CPU reference max error 0.0. |
| JTAG target | DEFERRED | Hardware Manager found no target; USB probe did not show Xilinx/Digilent cable. |
| Bitstream implementation/programming | DEFERRED | No hardware target/programming evidence. |
| FPGA hardware execution | DEFERRED | No physical execution evidence. |
| FPGA XRT C++ host API | DEFERRED | Host XRT headers unavailable per M9 dependency inventory. |
| Ubuntu 24.04.4 official support | UNKNOWN / not established | Native installation success does not change the official support matrix. |
| Qwen Q8 Vulkan inference | FAILED as separate M7.1 smoke | Kept isolated in Qwen evidence; no high-load/stability PASS is implied. |

## Rebuild order

Follow the ordered checklist in [`AI370_2_PLATFORM_RECORD.md`](AI370_2_PLATFORM_RECORD.md): verified recovery checkpoint → protected-stack version check → approved Xilinx 2026.1 install → device/board/platform closure → license without secret Git material → RTL and HLS synthesis → HIP/Vulkan/XRT/NPU/CNN regressions → hardware/JTAG validation when physically attached. Current records document a manually executed and explored flow; they are not an automated installer and should not be represented as one.

## M9/M10 completion state and next phase

M9 software FPGA toolchain validation is **PASS** and the `ai370-2-fpga-toolchain-working` tag remains at `0b8c922`. M10 Vitis/compiler/HLS/platform validation is **PASS** at `1d5f6fa`. Physical FPGA operations remain outside those PASS scopes and are **DEFERRED under M11** until a JTAG target is detected.
