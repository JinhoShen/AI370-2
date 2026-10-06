# Existing Vivado license under Codex workspace-write sandbox

**Date:** 2026-10-06 (Asia/Taipei)

## Comparison

| Check | Host shell | Default Codex `workspace-write` | Finding |
|---|---|---|---|
| `HOME` / effective user | `/home/shen` / UID 1000 | Same | No home/user mismatch |
| License-related environment variables | Unset | Unset | Matches the previously verified working invocation; no new variable required |
| Existing license file | Readable | Readable | No copy, reinstall, or permission change required |
| License parent / Vivado user data write access | Writable | Read-only mount | Tested an alternate writable HOME and explicit reference to the same existing license; checkout still failed |
| Network namespace / host identity | Licensed host NIC and its MAC are visible | Namespace isolation hides the licensed host NIC/MAC | FlexNet host-locked license checkout fails because its bound identity is unavailable |
| Vivado synthesis | PASS outside sandbox | License checkout failed in default sandbox | Same Vivado 2026.1 and same disposable project |

## Minimal verified workaround

Run only the licensed tool task with a one-command Codex override:

```sh
codex exec --sandbox workspace-write -C <disposable-project> \
  -c 'sandbox_workspace_write.network_access=true' <bounded task>
```

This restores visibility of the host NIC/MAC required by the host-locked FlexNet license while retaining the workspace-write filesystem sandbox. In that invocation, Vivado detected the existing valid license and synthesis exited 0. The same setting also allowed the unchanged XSim/Vivado runner to complete. No persistent Codex setting was changed. Host network access is enabled for the scope of that invocation, so keep the override limited to licensed-tool use.

## Unchanged state / privacy

- Existing license source and contents were neither replaced nor read into evidence.
- No license key, host ID, MAC address, or raw FlexNet diagnostic was retained.
- No Vivado/Vitis files or configuration, protected GPU/NPU stack, package, kernel, AppArmor policy, or global sandbox setting was changed during this diagnosis.
- M11/M12 projects and SP701 hardware were not accessed for build/program operations.
- T7 was not accessed.

The earlier AppArmor/Bubblewrap user-namespace failure and its authorized scoped-profile remediation are documented separately in [`codex-sandbox-diagnostic.md`](../codex-sandbox-diagnostic.md); this license issue was a distinct network-namespace/host-identity difference.
