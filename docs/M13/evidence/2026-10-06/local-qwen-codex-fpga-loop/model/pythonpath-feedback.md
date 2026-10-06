finish_reason: stop
model: qwen3.8-local

**Environment Adjustment:**
Export the missing variable before running the script to satisfy the strict shell mode:
`export PYTHONPATH="${PYTHONPATH:-}" && RUN_TAG=baseline ./scripts/run-validation.sh`

**Expected RTL Behavior Change:**
When `control_reg[1]` is high, the `REG_RESULT` read data should return the 32-bit unsigned sum of `input_reg` and `offset_reg` instead of the bitwise NOT of `input_reg`.
