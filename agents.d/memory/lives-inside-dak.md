---
name: lives-inside-dak
description: emoji.sh and icon.sh write into KIT_DIR="../Sources/DiscourseAssetKit" — this repo only functions when checked out at dak/discourse-assets (the declared submodule path); a standalone clone regenerates into nowhere.
metadata:
  type: project
---

Both entry scripts `cd "$(dirname "$0")"` and then use `KIT_DIR="../Sources/DiscourseAssetKit"`
(`emoji.sh:11`, `icon.sh:7`). Step 0.5 of `emoji.sh` also *reads* from there — it seeds
`assets/emojis/Emojis/` from the committed package Resources so a fresh clone skips the ~3,400-PNG
download.

**Why:** the repo is dak's asset *source*, declared in `dak/.gitmodules` at `discourse-assets`;
the harness materializes it there (`repos.toml`: `parent = "dak"`, `parent_path = "discourse-assets"`).

**How to apply:** never run the scripts from a clone that is not inside dak; if `../Sources`
is missing, stop — nothing will be written where the app can see it.
