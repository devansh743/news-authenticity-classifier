import os
import sys
import re
import html
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from google import genai as google_genai
except ImportError:
    google_genai = None

if genai is not None and not hasattr(genai, "Client"):
    if google_genai is not None and hasattr(google_genai, "Client"):
        genai.Client = google_genai.Client
    else:
        class _CompatClient:
            def __init__(self, *args, **kwargs):
                self.api_key = kwargs.get("api_key")
                self.models = self

            def generate_content(self, *args, **kwargs):
                raise RuntimeError("Google Generative AI SDK is unavailable in this environment.")

        genai.Client = _CompatClient

if genai is None and google_genai is not None:
    genai = google_genai
    if not hasattr(genai, "Client"):
        class _CompatClient:
            def __init__(self, *args, **kwargs):
                self.api_key = kwargs.get("api_key")
                self.models = self

            def generate_content(self, *args, **kwargs):
                raise RuntimeError("Google Generative AI SDK is unavailable in this environment.")

        genai.Client = _CompatClient

# Load environment variables from local .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def is_url(text):
    """
    Checks if a string is a web URL.
    """
    if not text:
        return False
    text = text.strip()
    if re.match(r"^https?://", text, re.IGNORECASE) or text.lower().startswith("www."):
        return True
    # Match domain-like structures (e.g. bbc.com/news/...)
    if re.match(r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+/", text):
        return True
    return False


def fetch_article_from_url(url):
    """
    Fetches article content, title, and source metadata directly from a web URL.
    """
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise ValueError(f"Unable to fetch content from URL ({url}): {exc}")

    # Extract title using multiple meta fallback strategies
    title = ""
    og_match = re.search(r'property=[\x22\x27]og:title[\x22\x27]\s+content=[\x22\x27](.*?)[\x22\x27]', raw_html, re.I)
    if not og_match:
        og_match = re.search(r'content=[\x22\x27](.*?)[\x22\x27]\s+property=[\x22\x27]og:title[\x22\x27]', raw_html, re.I)
    if og_match:
        title = html.unescape(og_match.group(1)).strip()

    if not title:
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', raw_html, re.I | re.S)
        if h1_match:
            clean_h1 = re.sub(r'<[^>]+>', '', h1_match.group(1))
            title = html.unescape(clean_h1).strip()

    if not title:
        title_match = re.search(r'<title>(.*?)</title>', raw_html, re.I | re.S)
        if title_match:
            title = html.unescape(title_match.group(1)).strip()

    if title:
        title = re.sub(r'\s*[-|–—]\s*[^|-–—]+$', '', title).strip() or title

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    domain_name = domain.split(".")[0].capitalize() if domain else "Web Source"

    cleaned = re.sub(r"<script.*?</script>", " ", raw_html, flags=re.I | re.S)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    words = cleaned.split()
    if len(words) < 20:
        raise ValueError("The target URL did not return sufficient readable article text.")

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.split()) > 8]
    article_text = " ".join(sentences[:25]) if sentences else cleaned[:2000]
    preview = article_text[:280] + ("..." if len(article_text) > 280 else "")

    if not title:
        title = preview[:80] + "..." if len(preview) > 80 else preview

    return {
        "title": title,
        "description": preview,
        "content": article_text,
        "url": url,
        "source": {"name": domain_name, "url": url},
    }


def fetch_from_google_news_rss(keyword):
    """
    Fetches news articles from Google News RSS feed without requiring an API key.
    """
    encoded_query = quote(keyword.strip())
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    req = Request(rss_url, headers=headers)
    with urlopen(req, timeout=10) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    item = root.find(".//item")
    if item is None:
        return None

    title = item.findtext("title", default="").strip()
    link = item.findtext("link", default="").strip()
    pub_date = item.findtext("pubDate", default="").strip()

    source_elem = item.find("source")
    source_name = (
        source_elem.text.strip()
        if source_elem is not None and source_elem.text
        else "Google News"
    )

    # Clean description HTML if present
    description = item.findtext("description", default="").strip()
    description = re.sub(r"<[^>]+>", " ", description).strip()
    description = html.unescape(description)

    return {
        "title": title,
        "description": description or title,
        "content": description or title,
        "url": link,
        "source": {"name": source_name, "url": link},
        "publishedAt": pub_date,
    }


def fetch_live_news(keyword):
    """
    Fetches the latest article matching the keyword or direct URL.
    - If keyword is a URL, fetches article text directly from the target page.
    - If GNews API key is available, queries GNews API.
    - If GNews API key is missing, fails, returns non-200, or has no articles, falls back to Google News RSS feed.
    """
    query = keyword.strip()
    if not query:
        raise ValueError("Please provide a keyword or article URL.")

    # 1. Direct URL handling
    if is_url(query):
        return fetch_article_from_url(query)

    # 2. GNews API attempt (if key available)
    api_key = os.environ.get("GNEWS_API_KEY") or os.environ.get("NEWS_API_KEY")
    if api_key:
        try:
            url = f"https://gnews.io/api/v4/search?q={quote(query)}&lang=en&apikey={api_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    return articles[0]
        except Exception:
            pass  # Fall back to RSS

    # 3. RSS Fallback (Requires no API key)
    try:
        rss_article = fetch_from_google_news_rss(query)
        if rss_article:
            return rss_article
    except Exception:
        pass

    raise ValueError(f"No news articles found for: '{query}'")


def format_article_for_analysis(article):
    """
    Formats the news article dictionary into a single string for analysis.
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
    if content and content != description:
        parts.append(f"Content: {content}")

    return "\n".join(parts)


def analyze_news_with_gemini(news_text, local_fallback_fn=None):
    """
    Sends the article content to Gemini to evaluate for misinformation.
    Uses the google-genai SDK.
    If GEMINI_API_KEY is missing or the call fails, optionally uses local_fallback_fn.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            if genai is None:
                raise RuntimeError("Google GenAI SDK is not installed.")

            if not hasattr(genai, "Client"):
                raise RuntimeError("Google GenAI client is unavailable in this environment.")

            client = genai.Client(api_key=api_key)
            prompt = f"""Analyze this news snippet for potential misinformation.
Look for sensationalism, logical fallacies, or missing context.
Provide a trust score out of 10 (format: "Trust Score: X/10") and a brief explanation.

News to analyze:
{news_text}
"""
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text
        except Exception as exc:
            if not local_fallback_fn:
                raise RuntimeError(f"Gemini API call failed: {exc}")

    # Fallback to local NLP classifier if Gemini key is absent or failed
    if local_fallback_fn:
        try:
            res = local_fallback_fn(news_text)
            notice = None
            if isinstance(res, (tuple, list)):
                if len(res) >= 4:
                    pred, conf, exp, notice = res[0], res[1], res[2], res[3]
                elif len(res) == 3:
                    pred, conf, exp = res[0], res[1], res[2]
                else:
                    pred, conf, exp = "UNKNOWN", None, {}
            else:
                pred, conf, exp = "UNKNOWN", None, {}

            if conf is not None:
                trust_score = round(conf / 10, 1) if pred == "REAL" else round((100 - conf) / 10, 1)
                conf_str = f"{conf}%"
            else:
                trust_score = 5.0 if pred == "REAL" else (0.0 if pred == "FAKE" else 5.0)
                conf_str = "N/A"

            matched_sigs = (
                ", ".join(exp.get("keywords", []))
                if isinstance(exp, dict) and exp.get("keywords")
                else "None"
            )
            top_words = (
                ", ".join(exp.get("top_words", []))
                if isinstance(exp, dict) and exp.get("top_words")
                else "None"
            )
            notice_str = f"\n• Notice: {notice}" if notice else ""

            return (
                f"Trust Score: {trust_score}/10\n\n"
                f"NLP Classifier Evaluation:\n"
                f"• Verdict: {pred} ({conf_str} confidence)\n"
                f"• Matched News Signals: {matched_sigs}\n"
                f"• Key Keywords: {top_words}"
                f"{notice_str}"
            )
        except Exception as fallback_exc:
            raise RuntimeError(f"Analysis failed: {fallback_exc}")

    raise RuntimeError(
        "Gemini API Key is missing. Please set the GEMINI_API_KEY environment variable."
    )

