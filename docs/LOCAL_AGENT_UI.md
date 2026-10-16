# AI370-2 local operation UI

Open **http://127.0.0.1:13306/** on this workstation. The user service `ai370-local-ui.service` is enabled. No cloud/CDN, new package, Codex runtime or external network endpoint is required for the page. Existing Lemonade and Ross local services remain prerequisites for their respective functions.

## Use

1. Select an installed model. The selector distinguishes historical engineering verification, present-but-unverified variants and retired entries.
2. Click **載入選定模型** when changing models. The current model and device are displayed separately from your selection. Wait until loading finishes before sending a task.
3. Choose **對話／專案唯讀查詢** for questions and safe repository text-file inspection. This mode exposes no patch or command tools.
4. Choose **隔離 RTL 修復＋XSim** or **隔離 RTL 修復＋XSim＋Vivado 綜合** only for the existing fixed T1 task: a fresh sandbox copies the unchanged task, testbench and seeded RTL. Only its one RTL file is editable. The Vivado option additionally runs a trusted fixed batch synthesis after the model completes XSim repair, targeting xc7s100fgga676-2. It records utilization and timing reports; missing I/O delays mean no timing-closure claim. The controller does not author or change model RTL. This is not arbitrary Tcl, arbitrary-project control, implementation, bitstream generation or FPGA programming.
5. Optionally enable real Ross Skills/local Knowledge Base. Progress lists actual tool events. **停止目前工作** requests cancellation and terminates the owned tool process tree; it does not restart the model service.

Each task is independent, with its request, result, trace and logs under `output/local-ui/<job-id>/`. Conversation completion is `COMPLETED`, not engineering PASS. An RTL task gets PASS only if the existing validator confirms a model-authored patch, baseline failure and post-patch XSim success. Golden projects are not editable through this UI.

## Model availability — actual local inventory, 2026-10-16

| Model | Local status |
|---|---|
| Qwen3.8-27B-UD-Q4_K_XL | Existing formal ENGINEERING model, historical engineering verification |
| Qwen3.8-27B-UD-Q4_K_M | File present and Lemonade registered; no new engineering acceptance claimed |
| Qwen3.8-27B-Uncensored-Q4_K_M | File present and registered; no new engineering acceptance claimed |
| gemma-4-31b-jang-crack-Q4_K_M | File present and registered; historical engineering verification |
| GPT-OSS 20B / Devstral Small 2 | Not found in readable home model/cache/download paths or Lemonade registry; old test roster says NOT_INSTALLED |
| Fifth provider/model | RESERVED, unspecified |
| Qwen3.6 entries | RETIRED and disabled in selector; no inference performed |

Several older Qwen cache copies and mmproj files exist but are not additional current registered chat-model providers. Recovery directories denied to the current user were not opened; T7 was not accessed. No model was downloaded, deleted or newly registered.

## Switching and safety

- Only model paths already reported by Lemonade and existing directly under the configured local GGUF root can be loaded. Retired models are rejected server-side.
- One UI action at a time; a busy resident model blocks a new action. External clients remain responsible for not starting concurrent workloads after the preflight.
- Existing offline/no-fetch settings must be enabled before loading. Unload the previous large model, then load the selection. Never use `--save-options`; the formal model's saved recipe remains unchanged.
- Non-formal selections request the installed Vulkan backend with 16K context and all available logical CPU threads, one slot. Availability does not establish that every model variant has passed engineering tests or that a backend cannot fail. Failed loads are recorded; the UI does not silently substitute another model. Select/load formal Qwen to return to the existing profile.
- Enforce available-memory, swap-growth, kernel-fault and finite-time guards. A failed/cancelled switch can leave no model resident; the UI reports current actual residency rather than claiming automatic recovery.
- Read-only mode filters tools and also rejects mutation at dispatch, even if a model invents a forbidden function call.
- Fixed engineering tools retain existing Bubblewrap and allowlist protection. Host NIC visibility remains necessary for the installed host-locked license; no license is installed or changed.
- Loopback binding only; exact Host/Origin checks, per-service-session request token, bounded JSON body, same-origin assets and CSP. Job files use private permissions. This protects against cross-site requests, not malicious software running as the same OS user.

## Service controls

```bash
systemctl --user status ai370-local-ui.service
systemctl --user restart ai370-local-ui.service
systemctl --user stop ai370-local-ui.service
journalctl --user -u ai370-local-ui.service --no-pager -n 30
```

Source: `scripts/local_agent_ui.py`, `scripts/local_ui/`, `scripts/ai370-local-ui.service`. Runs on Python standard library; browser assets are local. This UI addition does not change M15's PRE-FINAL verdict or complete Telegram/T7/new-machine rebuild/physical-air-gap acceptance.

## Initial UI acceptance — 2026-10-16, before Vivado follow-up

Readonly/chat E2E and browser-rendered selector PASS; 60 unit tests PASS. Formal Qwen exact ENGINEERING runtime and short API smoke PASS after fixing CLI reload argument restoration. Gemma selection hit the resource guard and was safely unloaded; this UI load configuration remains BLOCKED pending diagnosis. Other current Qwen variants are listed but not newly inferred. UI-specific XSim and real long-job cancellation remain NOT_TESTED. [All success/failure evidence](M13/evidence/2026-10-16/local-ui/README.md).

## Vivado follow-up — actual 2026-10-16 11:55–12:00

**PASS:** submit the `隔離 RTL 修復＋XSim＋Vivado 綜合` mode to run local Qwen/Ross repair, baseline XSim FAIL → model patch → XSim PASS → trusted Vivado batch synthesis. One patch, two XSim runs, 287.066 seconds. Real synthesis exit 0; utilization 123 LUTs / 178 registers / 0 BRAM / 0 DSP. Timing report only; no timing closure, implementation, bitstream or programming. 62 unit tests PASS, current formal runtime PASS. The earlier NOT_TESTED statement applies to the initial UI checkpoint and is superseded for this bounded mode only. [Full actual evidence](M13/evidence/2026-10-16/local-ui-vivado/README.md).
