import unittest
from unittest.mock import patch

import ai_provider_manager


class ApiKeyPoolTests(unittest.TestCase):
    @patch("ai_provider_manager.requests.post")
    def test_groq_uses_next_key_after_rate_limit(self, post):
        limited_response = unittest.mock.Mock(status_code=429)
        success_response = unittest.mock.Mock(status_code=200)
        success_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        post.side_effect = [limited_response, success_response]

        with patch.object(ai_provider_manager, "GROQ_API_KEYS", ("first", "second")):
            result = ai_provider_manager.call_groq("prompt")

        self.assertEqual(result, "response")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args_list[1].kwargs["headers"]["Authorization"],
            "Bearer second",
        )

    @patch("ai_provider_manager.requests.post")
    def test_gemini_uses_next_key_after_rejection(self, post):
        rejected_response = unittest.mock.Mock(status_code=403, ok=False)
        success_response = unittest.mock.Mock(status_code=200, ok=True)
        success_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "response"}]}}]
        }
        post.side_effect = [rejected_response, success_response]

        with patch.object(
            ai_provider_manager, "GEMINI_API_KEYS", ("first", "second")
        ):
            result = ai_provider_manager.call_gemini("prompt")

        self.assertEqual(result, "response")
        self.assertEqual(post.call_count, 2)
        self.assertIn("key=second", post.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
