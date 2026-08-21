import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure project root is in the path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import news_pipeline

class NewsPipelineTests(unittest.TestCase):

    def setUp(self):
        # Store original environment variables
        self.orig_gnews_key = os.environ.get("GNEWS_API_KEY")
        self.orig_news_key = os.environ.get("NEWS_API_KEY")
        self.orig_gemini_key = os.environ.get("GEMINI_API_KEY")

        # Clear them by default for test isolation where needed
        os.environ.pop("GNEWS_API_KEY", None)
        os.environ.pop("NEWS_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self):
        # Restore environment variables
        if self.orig_gnews_key is not None:
            os.environ["GNEWS_API_KEY"] = self.orig_gnews_key
        if self.orig_news_key is not None:
            os.environ["NEWS_API_KEY"] = self.orig_news_key
        if self.orig_gemini_key is not None:
            os.environ["GEMINI_API_KEY"] = self.orig_gemini_key

    @patch("news_pipeline.requests.get")
    def test_fetch_live_news_success(self, mock_get):
        os.environ["GNEWS_API_KEY"] = "fake_gnews_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "articles": [
                {
                    "title": "Breaking Election News",
                    "description": "Results are rolling in.",
                    "content": "Full article content goes here...",
                    "url": "https://example.com/election",
                    "source": {"name": "Test Source", "url": "https://example.com"}
                }
            ]
        }
        mock_get.return_value = mock_response

        article = news_pipeline.fetch_live_news("election")
        self.assertEqual(article["title"], "Breaking Election News")
        self.assertEqual(article["url"], "https://example.com/election")
        mock_get.assert_called_once_with(
            "https://gnews.io/api/v4/search?q=election&lang=en&apikey=fake_gnews_key",
            timeout=10
        )

    def test_fetch_live_news_missing_key(self):
        with self.assertRaises(RuntimeError) as context:
            news_pipeline.fetch_live_news("election")
        self.assertIn("GNews API Key is missing", str(context.exception))

    @patch("news_pipeline.requests.get")
    def test_fetch_live_news_no_articles(self, mock_get):
        os.environ["NEWS_API_KEY"] = "fake_news_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"articles": []}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            news_pipeline.fetch_live_news("nothing_here")
        self.assertIn("No news articles found", str(context.exception))

    @patch("news_pipeline.requests.get")
    def test_fetch_live_news_error_status(self, mock_get):
        os.environ["GNEWS_API_KEY"] = "fake_gnews_key"

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden / Invalid Key"
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            news_pipeline.fetch_live_news("election")
        self.assertIn("returned status code 403", str(context.exception))

    def test_format_article_for_analysis_dict(self):
        article = {
            "title": "A Great Title",
            "description": "Short description.",
            "content": "Body text of the story."
        }
        formatted = news_pipeline.format_article_for_analysis(article)
        self.assertIn("Title: A Great Title", formatted)
        self.assertIn("Description: Short description.", formatted)
        self.assertIn("Content: Body text of the story.", formatted)

    def test_format_article_for_analysis_string(self):
        raw_text = "Just raw string data."
        formatted = news_pipeline.format_article_for_analysis(raw_text)
        self.assertEqual(formatted, raw_text)

    @patch("news_pipeline.genai.Client")
    def test_analyze_news_with_gemini_success(self, mock_client_class):
        os.environ["GEMINI_API_KEY"] = "fake_gemini_key"

        # Setup mock client chain: client.models.generate_content(...)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Trust Score: 9/10\nReason: Verifiable facts."
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = news_pipeline.analyze_news_with_gemini("News text to evaluate.")

        mock_client_class.assert_called_once_with(api_key="fake_gemini_key")
        mock_client.models.generate_content.assert_called_once()
        self.assertIn("Trust Score: 9/10", result)

    def test_analyze_news_with_gemini_missing_key(self):
        with self.assertRaises(RuntimeError) as context:
            news_pipeline.analyze_news_with_gemini("Some text")
        self.assertIn("Gemini API Key is missing", str(context.exception))

    @patch("news_pipeline.genai.Client")
    def test_analyze_news_with_gemini_failure(self, mock_client_class):
        os.environ["GEMINI_API_KEY"] = "fake_gemini_key"

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Quota Exceeded")
        mock_client_class.return_value = mock_client

        with self.assertRaises(RuntimeError) as context:
            news_pipeline.analyze_news_with_gemini("Some text")
        self.assertIn("Gemini API call failed", str(context.exception))

if __name__ == "__main__":
    unittest.main()
