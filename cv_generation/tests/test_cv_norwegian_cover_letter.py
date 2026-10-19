"""Tests for Norwegian B1 cover letter localization voice and postprocess."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_norwegian import (
    build_localization_prompt,
    count_norwegian_cover_letter_body_words,
    postprocess_norwegian_cover_letter,
)
from cv_generation.cv_style import (
    NORWEGIAN_B1_COVER_LETTER_VOICE,
    NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS,
    NORWEGIAN_COVER_LETTER_LENGTH_HINT,
)


class TestNorwegianCoverLetterVoice(unittest.TestCase):
    def test_voice_includes_personality_and_team_fit(self) -> None:
        joined = " ".join(NORWEGIAN_B1_COVER_LETTER_VOICE).lower()
        self.assertIn("personality", joined)
        self.assertIn("team fit", joined)

    def test_voice_includes_length_guidance(self) -> None:
        joined = " ".join(NORWEGIAN_B1_COVER_LETTER_VOICE)
        self.assertIn(str(NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS), joined)
        self.assertIn(NORWEGIAN_COVER_LETTER_LENGTH_HINT, NORWEGIAN_B1_COVER_LETTER_VOICE)

    def test_localization_prompt_includes_length_and_personality(self) -> None:
        prompt = build_localization_prompt(
            "cover-letter",
            "MITCH EVANS\n\n**Re: Role**\n\nBody.\n",
            track="industry",
            samples="",
        )
        payload = json.loads(prompt)
        constraints = " ".join(payload["constraints"])
        self.assertIn("250", constraints)
        self.assertIn("350", constraints)
        self.assertIn("personality", constraints.lower())
        self.assertIn("team fit", constraints.lower())
        self.assertIn("shorten", payload["instruction"].lower())

    def test_postprocess_warns_when_body_too_long(self) -> None:
        long_body = " ".join(["ord"] * (NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS + 40))
        letter = (
            "MITCH EVANS\n\n**Ang: Utvikler**\n\n"
            f"{long_body}\n\n"
            "Med vennlig hilsen,\n\nMITCH EVANS\n"
        )
        _, warnings = postprocess_norwegian_cover_letter(letter)
        self.assertTrue(any("words" in w for w in warnings))

    def test_count_body_words_excludes_header_and_signature(self) -> None:
        letter = (
            "MITCH EVANS\n\n**Ang: Utvikler**\n\n"
            "Jeg liker å jobbe i team.\n\n"
            "Med vennlig hilsen,\n\nMITCH EVANS\n"
        )
        self.assertEqual(count_norwegian_cover_letter_body_words(letter), 6)


if __name__ == "__main__":
    unittest.main()
