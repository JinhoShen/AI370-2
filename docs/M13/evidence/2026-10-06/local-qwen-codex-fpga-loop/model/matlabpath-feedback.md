finish_reason: stop
model: qwen3.8-local

The error `MATLABPATH: unbound variable` indicates that the Vitis script is using `set -u` (nounset) and attempting to expand a variable that is not defined in the environment.

**Next environment-only adjustment:**

Export an empty `MATLABPATH` before running the baseline:

```bash
export MATLABPATH="${MATLABPATH:-}"
```

**Instruction to agent:**
Set `MATLABPATH` to an empty string (or its current value if set) in the environment, then retry the baseline command.
