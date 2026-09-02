---
name: forum-url-defaults
description: emoji.sh defaults FORUM_URL to https://forum.dirtbikechina.com (the STAGE forum) because meta.discourse.org does not expose search_aliases and has an extra default group; icon.sh defaults to https://meta.discourse.org. Override with FORUM_URL=… for either.
metadata:
  type: project
---

`emoji.sh:10` — `FORUM_URL="${FORUM_URL:-https://forum.dirtbikechina.com}"`, with the comment
that meta.discourse.org "does not expose search aliases, and has an extra default group which is
not ideal for the script to process into EmojiItem". `icon.sh:6` —
`FORUM_URL="${FORUM_URL:-https://meta.discourse.org}"`. Emoji data also pulls
`frontend/pretty-text/addon/emoji/data.js` from the upstream Discourse repo (`emoji.sh:12`).

**Why:** the emoji export depends on a self-hosted setting; icons are upstream's sprite.

**How to apply:** regenerating emoji means the stage forum must be up and reachable; use
`FORUM_URL=https://forum.dirtbikex.com bash emoji.sh` only deliberately — prod and stage can have
different custom emoji sets. `dbx env` on the box tells you which apex you are on.
