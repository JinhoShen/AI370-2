# M10 Vitis / HLS / platform validation — PASS

Date: 2026-10-01 (Asia/Taipei). Continued from M9 working-state commit `0b8c922`; no tool reinstall and no protected system-stack changes were made. This is native Ubuntu 24.04.4 validation, not a claim of official OS support.

## VERIFIED

- Vitis Unified 2026.1 and the separate Vitis Embedded 2026.1 installation start and report the expected version. Vitis HLS runs through `vitis-run` in the Unified 2026.1 tree; the M9 SP701 C synthesis report and full log record the actual synthesis.
- `v++ --version` reports v2026.1 and exits successfully: `evidence/2026.1/vpp-version.log`.
- Vitis HLS C synthesis compiled and synthesized `m9_adder` for the SP701 Spartan-7 part `xc7s100-fgga676-2`, producing the report and RTL artifacts recorded in `../M9/evidence/license-unlocked-2026.1/synthesis/`. The runner and complete output are in `../M9/native-toolchain-smoke/run_hls_smoke.sh` and `../M9/evidence/native-2026.1/logs/hls-license-smoke-console.log`.
- All eight installed embedded `.xpfm` platforms were enumerated and then parsed individually using `platforminfo -p`; the fresh per-platform output is `evidence/2026.1/platform-parse.log` and the platform list is in `../M9/evidence/license-unlocked-2026.1/logs/embedded-platform-list.json`.
- Vitis Embedded version/startup evidence is retained in `../M9/evidence/native-2026.1/logs/vitis-embedded-license-version.log` plus the earlier GUI startup logs.

## Scope limits

The platform checks prove that Vitis recognizes and reads those embedded platform files. They do not prove build/implementation on each platform or execution on a physical board. The SP701 has no connected JTAG target in the Hardware Manager probe; bitstream programming and live FPGA behavior remain DEFERRED under M11. FPGA acceleration XRT card runtime and host XRT API development remain DEFERRED/UNKNOWN as recorded in `../M9/ACCELERATION_INSTALL_RESULT.md`.

**M10 Vitis version/compiler/HLS/platform software checks: PASS.** M9 remains PASS at `../M9/LICENSE_UNLOCKED_VALIDATION.md`; the M9 tag `ai370-2-fpga-toolchain-working` is unchanged.
