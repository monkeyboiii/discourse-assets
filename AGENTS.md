# AGENTS.md — discourse-assets

The repo contract. Everything else an agent needs is under `agents.d/` — shape and rules in the
harness's `playbook/agents-d.md`.

- Read `agents.d/memory/MEMORY.md` first: three facts, each of which will bite otherwise.
- This repo only works **from `dak/discourse-assets`**: `emoji.sh` and `icon.sh` write to
  `../Sources/DiscourseAssetKit`. Do not run it from anywhere else.
- Nothing here runs on the Linux dev box (no `uv`); the regeneration skill documents the loop
  for a Mac. Editing the Python is fine anywhere; running it is not.
- `src/shared/shortcode.py` and dak's `Emoji+Init.swift` implement the same sanitizer.
  **Edit both or neither.**
- Surgical, simple, never invent a path — the harness `AGENTS.md` discipline applies here.
