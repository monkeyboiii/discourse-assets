# agents.d

What an agent needs about discourse-assets, in one place:

- `memory/` — facts true only for this repo; read `MEMORY.md` first, then only what applies.
- `modules/` — the docs (`ASSET_PIPELINE.md`, the runbook that was the README).
- `skills/` — `discourse-assets-regen`, the regeneration loop; linked into the harness by
  `dbx skills sync`, described by `dbx skills show discourse-assets-regen`.

Shape, rules and rollout: `dirtbikex-agent-coding/playbook/agents-d.md`. Pilot repo, 2026-09-02.
