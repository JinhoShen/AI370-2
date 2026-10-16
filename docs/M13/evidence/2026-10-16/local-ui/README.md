# Local UI actual acceptance — 2026-10-16

Loopback UI on 127.0.0.1:13306 is installed/enabled as a user service. No package, driver, model, license or protected stack was installed or replaced. Python standard-library server and local assets reuse the existing Local Agent.

## Actual results

- Real Firefox WebDriver BiDi inspection confirmed six selector entries: four present current variants and two disabled retired Qwen3.6 entries; connection status and job history rendered. Screenshot retained. This is browser rendering evidence, not a browser-clicked engineering test.
- UI HTTP API → Local Agent → existing local Qwen → result: COMPLETED, exact LOCAL_UI_READY, 9.52 seconds. No Codex or cloud runtime.
- Same-model ready selection: completed without reloading.
- Cross-provider Gemma switch: FAIL / resource guard. At 15.605 seconds the configured maximum host swap-growth threshold of 64 MiB (or available-memory floor) stopped loading; exact per-sample resource values were not persisted, so do not assert the measured overshoot or OOM. No Gemma inference was run. Earlier historical Gemma engineering PASS remains valid for its old configuration. This current load configuration is blocked from UI retries, including after a UI restart; diagnosis is required before retry. No memory guard was relaxed.
- Initial Qwen return loaded the right model but subsequent exact profile verifier found missing --n-gpu-layers. This was a controller restoration defect, not a model reasoning failure. Raw result and failing verifier are retained. Lemonade's registered saved recipe was still unchanged; bare CLI load did not apply all options.
- Fix: every actual UI load now sends explicit backend/context/layer/thread parameters; formal Qwen additionally gets its exact measured batch/FA/KV settings. Never --save-options. Final formal reload completed in 5.927 seconds; exact ENGINEERING verifier and bounded four-token API smoke PASS. Final inference did not use a second large model.
- 60 unit tests PASS, including readonly mutation rejection, missing/retired model rejection, no fallback, cross-origin/Host/CSRF protection, parallel-task rejection, explicit formal parameters and persistence of guarded-load suspension. JS syntax check and Python compilation PASS.
- Targeted readable kernel audit: no matching new fault. No active UI job remained at final check. Service active, only listening on 127.0.0.1.

## Boundaries

UI readonly/chat and HTTP safety acceptance PASS. Actual provider switching is PARTIAL because the Gemma load hit a resource gate. Other Qwen variants are present but were not loaded/inferred in this UI acceptance. Fixed RTL/XSim mode reuses previously verified sandbox/validator code; no new UI-triggered XSim or FPGA programming was performed. Stop endpoint/authentication was unit-tested; cancellation of a real long model job is NOT_TESTED. No GPT-OSS or Devstral artifact was found in scanned readable home resources/caches/downloads; inaccessible recovery directories and T7 were not searched. This does not change M15 PRE-FINAL or complete physical air-gap, Telegram, or new-machine deployment.
