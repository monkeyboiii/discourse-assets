"""Parity tests for sanitize_shortcode_to_asset.

Mirror of Swift test cases against
``DiscourseEmoji.sanitizeShortcodeToAssetName`` in Emoji+Init.swift.
When a case here changes, the Swift side must change identically.
"""

from __future__ import annotations

import unittest

from src.shared.shortcode import sanitize_shortcode_to_asset as sanitize


class SanitizeShortcodeTests(unittest.TestCase):
    def test_basic_with_colons(self):
        self.assertEqual(sanitize(":grinning_face:"), "emoji_grinning_face")

    def test_basic_without_colons(self):
        self.assertEqual(sanitize("grinning_face"), "emoji_grinning_face")

    def test_plus_one(self):
        self.assertEqual(sanitize(":+1:"), "emoji_plus_one")
        self.assertEqual(sanitize("+1"), "emoji_plus_one")

    def test_minus_one(self):
        self.assertEqual(sanitize(":-1:"), "emoji_minus_one")
        self.assertEqual(sanitize("-1"), "emoji_minus_one")

    def test_special_chars_become_underscore(self):
        self.assertEqual(sanitize(":a&b:"), "emoji_a_b")
        self.assertEqual(sanitize(":a.b.c:"), "emoji_a_b_c")

    def test_consecutive_underscores_collapsed(self):
        self.assertEqual(sanitize(":a___b:"), "emoji_a_b")
        self.assertEqual(sanitize(":a  b:"), "emoji_a_b")

    def test_leading_and_trailing_underscores_stripped(self):
        self.assertEqual(sanitize(":_foo_:"), "emoji_foo")
        self.assertEqual(sanitize(":__foo__:"), "emoji_foo")

    def test_empty_becomes_unknown(self):
        self.assertEqual(sanitize("::"), "emoji_unknown")
        self.assertEqual(sanitize(""), "emoji_unknown")

    def test_only_special_chars_becomes_unknown(self):
        self.assertEqual(sanitize(":&&&:"), "emoji_unknown")
        self.assertEqual(sanitize(":---:"), "emoji_unknown")

    def test_case_is_preserved(self):
        self.assertEqual(sanitize(":FooBar:"), "emoji_FooBar")

    def test_digits_allowed(self):
        self.assertEqual(sanitize(":1st_place:"), "emoji_1st_place")
        self.assertEqual(sanitize(":100:"), "emoji_100")

    def test_plus_one_only_matches_exact(self):
        # "+1_something" is NOT the +1 special case; it hits the regex path.
        self.assertEqual(sanitize(":+1_something:"), "emoji_1_something")


if __name__ == "__main__":
    unittest.main()
