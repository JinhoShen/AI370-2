finish_reason: length
model: qwen3.8-local

The correct next diagnostic/action is to **verify and configure the Vivado license environment variables** (`LM_LICENSE_FILE` or `VIVADO_LICENSE_FILE`) to point to a valid, accessible license server or local license file.

**Reasoning:**
1.  **Root Cause Identification:** The explicit error `Vivado Design Suite cannot be launched because a valid license was not found` indicates that the failure is environmental/licensing, not functional or RTL-related. The subsequent TCL exception and exit code 14 are downstream consequences of the Vivado launch failure.
2.  **Constraint Adherence:**
    *   **No functional PASS claimed:** The run failed at launch; no simulation results were generated.
    *   **No RTL edits:** The source is unchanged, and the error is unrelated to code logic.
    *   **No license suppression:** The action focuses on providing a valid license, not bypassing the check.
3.  **Corrective Action:** Since `PYTHONPATH` and `MATLABPATH` were already cleared (ruling out path
