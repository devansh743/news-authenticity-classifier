import unittest
from unittest.mock import patch

import app
from werkzeug.security import generate_password_hash


class AppLogicTests(unittest.TestCase):
    def test_is_news_accepts_real_article_text(self):
        text = "President Joe Biden announced a new economic plan on Monday, saying the policy will help families across the country."
        self.assertTrue(app.is_news(text))

    def test_is_news_rejects_short_or_non_news_text(self):
        self.assertFalse(app.is_news("hello there this is just a greeting"))

    def test_normalize_text_cleans_whitespace(self):
        self.assertEqual(app.normalize_text("  Hello   world  \n\n  again  "), "Hello world again")

    def test_preview_returns_summary_text(self):
        text = "President Joe Biden announced a new economic plan on Monday. The policy aims to help families across the country. Analysts say the measure could improve local markets."
        self.assertIn("President Joe Biden", app.get_article_preview(text))
        self.assertIn("economic plan", app.get_article_preview(text))

    @patch("app.predict_article")
    def test_api_analyze_returns_prediction_for_article_text(self, mock_predict_article):
        mock_predict_article.return_value = ("REAL", 87.5, {"keywords": ["announced"], "top_words": ["policy"]})
        article_text = (
            "The committee released its annual update on infrastructure spending, "
            "noting that officials approved new contracts and expanded support for local transit projects across several cities. "
            "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
        )

        with app.app.test_client() as client:
            response = client.post("/api/analyze", data={"news": article_text})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["prediction"], "REAL")
        self.assertEqual(payload["confidence"], 87.5)
        self.assertIn("notice", payload)
        mock_predict_article.assert_called_once()

    @patch("app.predict_article")
    def test_api_analyze_warns_on_short_paragraph(self, mock_predict_article):
        mock_predict_article.return_value = ("FAKE", 64.2, {"keywords": [], "top_words": []})
        paragraph = "Officials announced a new transport plan today for downtown commuters and workers across the city center."

        with app.app.test_client() as client:
            response = client.post("/api/analyze", data={"news": paragraph})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["prediction"], "FAKE")
        self.assertIn("notice", payload)
        self.assertIn("short paragraph", payload["notice"].lower())
        mock_predict_article.assert_called_once()

    @patch("app.predict_article")
    def test_api_analyze_returns_not_news_for_off_topic_text(self, mock_predict_article):
        off_topic = "The blue chair sat beside the window while music played softly in the room."

        with app.app.test_client() as client:
            response = client.post("/api/analyze", data={"news": off_topic})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["prediction"], "NOT NEWS")
        self.assertIsNone(payload["confidence"])
        self.assertIn("notice", payload)
        self.assertIn("real/fake verdict was forced", payload["notice"].lower())
        mock_predict_article.assert_not_called()

    @patch("app.compute_features")
    @patch("app.model")
    def test_predict_article_prefers_real_when_fake_probability_is_below_threshold(self, mock_model, mock_compute_features):
        mock_compute_features.return_value = [[0]]
        mock_model.classes_ = [0, 1]
        mock_model.predict_proba.return_value = [[0.64, 0.36]]

        prediction, confidence, explanation = app.predict_article(
            "Officials announced a new infrastructure plan with updated contracts for city transit projects across several districts."
        )

        self.assertEqual(prediction, "REAL")
        self.assertEqual(confidence, 36.0)
        self.assertIsInstance(explanation, dict)

    @patch("app.get_db_connection")
    def test_register_logs_user_in_after_success(self, mock_get_db_connection):
        class FakeConn:
            def execute(self, *args, **kwargs):
                return self

            def commit(self):
                return None

            def close(self):
                return None

        mock_get_db_connection.return_value = FakeConn()
        with app.app.test_request_context(
            "/register",
            method="POST",
            data={"username": "alice", "email": "alice@example.com", "password": "secret123"},
        ):
            response = app.register()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(app.session.get("user"), "alice")

    @patch("app.get_db_connection")
    def test_login_accepts_username_or_email(self, mock_get_db_connection):
        class FakeConn:
            def __init__(self):
                self.user = {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": generate_password_hash("secret123"),
                }

            def execute(self, query, params):
                if "FROM users" in query:
                    if params[0] in ("alice", "alice@example.com") or params[1] in ("alice", "alice@example.com"):
                        return self
                    return self
                return self

            def fetchone(self):
                return self.user

            def close(self):
                return None

        mock_get_db_connection.return_value = FakeConn()

        with app.app.test_request_context(
            "/login",
            method="POST",
            data={"email": "alice", "password": "secret123"},
        ):
            response = app.login()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(app.session.get("user"), "alice")

        with app.app.test_request_context(
            "/login",
            method="POST",
            data={"email": "alice@example.com", "password": "secret123"},
        ):
            response = app.login()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(app.session.get("user"), "alice")


if __name__ == "__main__":
    unittest.main()
