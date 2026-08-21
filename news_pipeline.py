import os
import sys
import requests
from google import genai

# Load environment variables from local .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def fetch_live_news(keyword):
    """
    Fetches the latest article matching the keyword from GNews API.
    Raises RuntimeError if API keys are missing or GNews request fails.
    Raises ValueError if no articles are found.
    """
    api_key = os.environ.get("GNEWS_API_KEY") or os.environ.get("NEWS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GNews API Key is missing. Please set the GNEWS_API_KEY or NEWS_API_KEY environment variable."
        )

    url = f"https://gnews.io/api/v4/search?q={keyword}&lang=en&apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
    except Exception as exc:
        raise RuntimeError(f"GNews API request failed: {exc}")

    if response.status_code != 200:
        raise RuntimeError(
            f"GNews API returned status code {response.status_code}: {response.text}"
        )

    data = response.json()
    articles = data.get("articles", [])
    if not articles:
        raise ValueError(f"No news articles found for the keyword: '{keyword}'")

    return articles[0]


def format_article_for_analysis(article):
    """
    Formats the GNews article dictionary into a single string for analysis.
    If the input is already a string, returns it directly.
    """
    if isinstance(article, str):
        return article

    title = article.get("title", "")
    description = article.get("description", "")
    content = article.get("content", "")

    parts = []
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if content:
        parts.append(f"Content: {content}")

    return "\n".join(parts)


def analyze_news_with_gemini(news_text):
    """
    Sends the article content to Gemini to evaluate for misinformation.
    Uses the new google-genai SDK.
    Raises RuntimeError if GEMINI_API_KEY is missing or the API call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Gemini API Key is missing. Please set the GEMINI_API_KEY environment variable."
        )

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""Analyze this news snippet for potential misinformation.
Look for sensationalism, logical fallacies, or missing context.
Provide a trust score out of 10 (format: "Trust Score: X/10") and a brief explanation.

News to analyze:
{news_text}
"""
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        return response.text
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}")


if __name__ == "__main__":
    # Small runnable script/utility to execute end-to-end.
    keyword = "election"
    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:])

    print(f"--- FETCHING LIVE NEWS FOR KEYWORD: '{keyword}' ---")
    try:
        article = fetch_live_news(keyword)
        print(f"Fetched Article Title: {article.get('title')}")
        print(f"Source: {article.get('source', {}).get('name')} | URL: {article.get('url')}")

        news_text = format_article_for_analysis(article)
        print("\n--- FORMATTED TEXT FOR ANALYSIS ---")
        print(news_text)

        print("\n--- SENDING TO GEMINI DETECTION API ---")
        result = analyze_news_with_gemini(news_text)
        print("\n--- GEMINI DETECTION ANALYSIS RESULT ---")
        print(result)

    except Exception as exc:
        print(f"\n[ERROR] Pipeline run failed: {exc}", file=sys.stderr)
        sys.exit(1)
