# Codex Linux sandbox diagnostic

**Date:** 2026-10-06 (Asia/Taipei)
**Result:** Read-only diagnosis. No package, security profile, kernel, GPU, NPU or FPGA configuration was changed.

## Observed host state

- Codex CLI: `0.159.2`
- Ubuntu host: `24.04.4 LTS` (existing platform record)
- Bubblewrap: `0.9.0`, `/usr/bin/bwrap`
- AppArmor: `4.0.1really4.0.1-0ubuntu0.24.04.5`
- `kernel.apparmor_restrict_unprivileged_userns=1`
- `apparmor-profiles` is not installed; `/usr/share/apparmor/extra-profiles/bwrap-userns-restrict` and `/etc/apparmor.d/bwrap-userns-restrict` are absent.
- `unshare -Urn true` fails at writing `/proc/self/uid_map` with `Operation not permitted`.
- A Codex read-only sandbox probe fails with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.

These observations show that this host currently denies the unprivileged namespace operation required by the Codex Bubblewrap sandbox. The active AppArmor user-namespace restriction is consistent with the failure and with OpenAI's Ubuntu 24.04 troubleshooting guidance; an AppArmor audit record was not collected, so the exact kernel denial attribution is not independently confirmed.

## Candidate remediation and gate

OpenAI's [sandboxing guidance](https://learn.chatgpt.com/docs/sandboxing), accessed 2026-10-06, recommends installing the dedicated `bwrap-userns-restrict` AppArmor profile on Ubuntu 24.04 and loading it with AppArmor. It separately lists globally disabling `kernel.apparmor_restrict_unprivileged_userns` as a fallback; that broader option is not selected.

APT simulation for `apparmor-profiles apparmor-utils` planned four new packages and upgrades of `apparmor` and `libapparmor1` from `4.0.1really4.0.1-0ubuntu0.24.04.5` to `4.0.1really4.0.1-0ubuntu0.24.04.8`. It did not plan changes to the protected kernel, Mesa/libdrm, ROCm, XRT, amdxdna or NPU firmware packages. The scoped profile still changes active system security policy and requires administrative privileges. No install/profile load has been performed pending explicit authorization.

Until the profile is approved and loaded, Codex local text generation and tool-call dispatch remain VERIFIED, but local shell tool execution remains BLOCKED. No unconfined fallback was attempted.
