import unittest

from onepieceguess.engine import matches_guess, normalize, safe_wiki_hint


class GuessMatchingTests(unittest.TestCase):
    def test_normalizes_punctuation_and_case(self):
        self.assertEqual(normalize("Monkey D. Luffy!"), "monkey d luffy")

    def test_accepts_full_name_and_alias(self):
        self.assertTrue(matches_guess("MONKEY D LUFFY", "Monkey D. Luffy"))
        self.assertTrue(matches_guess("Straw Hat", "Monkey D. Luffy", ["Straw Hat"]))

    def test_accepts_non_first_name_token(self):
        self.assertTrue(matches_guess("Luffy", "Monkey D. Luffy"))

    def test_rejects_first_name_only_and_short_answers(self):
        self.assertFalse(matches_guess("Monkey", "Monkey D. Luffy"))
        self.assertFalse(matches_guess("Lu", "Monkey D. Luffy"))

    def test_accepts_small_typo_but_rejects_unrelated_answer(self):
        self.assertTrue(matches_guess("Monkey D Lufy", "Monkey D. Luffy"))
        self.assertFalse(matches_guess("Zoro", "Monkey D. Luffy"))

    def test_wiki_hint_redacts_answer_and_alias(self):
        hint = safe_wiki_hint("Monkey D. Luffy, also known as Straw Hat, is a pirate.",
                              "Monkey D. Luffy", ["Straw Hat"])
        self.assertNotIn("Luffy", hint)
        self.assertNotIn("Straw Hat", hint)

    def test_wiki_hint_has_safe_fallback_when_answer_is_the_intro(self):
        hint = safe_wiki_hint("Nami is a navigator.", "Nami")
        self.assertIn("blurred image", hint)


if __name__ == "__main__":
    unittest.main()
