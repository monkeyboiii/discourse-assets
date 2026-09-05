---
name: shortcode-sanitizer-mirrored
description: src/shared/shortcode.py::sanitize_shortcode_to_asset is mirrored by hand in dak at Sources/DiscourseAssetKit/Emoji/Emoji+Init.swift (sanitizeShortcodeToAssetName) — a change to either without the other silently breaks emoji lookup; edit both or neither.
metadata:
  type: project
---

The Python generator names asset files with one sanitizer; the Swift runtime derives the same
names with another. They are two implementations of one rule with no shared source and no test
across the boundary.

**Why:** recorded in `agents.d/modules/asset-pipeline.md § Shortcode sanitization` ("Edit both or
neither"). `tests/test_shortcode.py` covers only the Python side.

**How to apply:** any change to `sanitize_shortcode_to_asset` is a two-repo change — this repo
and dak — and the acceptance criterion is that a regenerated emoji resolves at runtime, which is
INSPECT-only on the Linux box.
