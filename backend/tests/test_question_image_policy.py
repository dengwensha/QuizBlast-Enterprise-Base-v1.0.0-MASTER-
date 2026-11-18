"""Regression checks for new image policy; no database dependency."""
import unittest
from app.services.question_image_policy import validate_question_image


class ImagePolicyTests(unittest.TestCase):
    def test_text_only_question_remains_valid(self):
        self.assertEqual(validate_question_image(None, None), (None, None))
        self.assertEqual(validate_question_image("", ""), (None, None))

    def test_public_https_image_and_alt_text(self):
        self.assertEqual(
            validate_question_image(" https://images.example.org/cat.png ", " Kedi resmi "),
            ("https://images.example.org/cat.png", "Kedi resmi"),
        )

    def test_reject_untrusted_protocol_and_private_addresses(self):
        urls = (
            "http://example.org/a.png", "javascript:alert(1)",
            "data:image/svg+xml,<svg></svg>", "blob:https://example.org/id",
            "/assets/picture.png", "https://user:pw@example.org/a.png",
            "https://localhost/p.png", "https://127.0.0.1/p.png",
            "https://192.168.1.1/a.png", "https://example.org:8080/p.png",
        )
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_question_image(url, "Alt")

    def test_reject_overlong_url_and_alt(self):
        with self.assertRaisesRegex(ValueError, "invalid_image_url"):
            validate_question_image("https://example.org/" + "a" * 2050, "")
        with self.assertRaisesRegex(ValueError, "image_alt_text_too_long"):
            validate_question_image("https://example.org/a.png", "a" * 241)

    def test_alt_requires_image(self):
        with self.assertRaisesRegex(ValueError, "image_alt_text_requires_image"):
            validate_question_image("", "Description")


if __name__ == "__main__":
    unittest.main()
