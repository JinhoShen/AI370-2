# Ross Skill runtime snapshot

These unmodified AMD Agent Skill directories are copied from the locally installed AMD Ross Agentic AI Assistant 2026.9.1 package so the standalone Qwen Local Agent can read Skills without launching Codex CLI or relying on Codex's plugin cache at runtime.

Source: `/home/shen/.codex/plugins/cache/amd-ross-agentic-ai-assistant/amd-ross-agentic-ai-assistant/2026.9.1/skills/`

Included skills:

- `vivado-simulate-rtl`
- `vivado-rtl-elaboration-analysis`
- `hls-run-flow`
- `hls-synthesizable`
- `hls-synth-report`

The runtime offers only these Skill names through `ross_skill_read`, and only reads `SKILL.md` plus an explicitly selected one-level markdown/text reference. It does not execute any scripts shipped by a Skill. `SHA256SUMS` records the snapshot contents. Source copyright and license notices are preserved.
