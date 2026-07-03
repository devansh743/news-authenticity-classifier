from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import pickle
import os
import json
import re
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from werkzeug.security import generate_password_hash, check_password_hash

ADMIN_EMAIL = "admin@fnd.com"
ADMIN_PASSWORD = "admin123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

# TF-IDF vectorizer used by the saved classifier artifact
VECT_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")
vectorizer = None
if os.path.exists(VECT_PATH):
    try:
        with open(VECT_PATH, 'rb') as vf:
            vectorizer = pickle.load(vf)
    except Exception:
        vectorizer = None

app = Flask(__name__)
app.secret_key = "secretkey123"

MIN_ANALYSIS_WORDS = 8
MIN_RELIABLE_WORDS = 25

NEWS_CUES = {
    "according",
    "announced",
    "article",
    "byline",
    "capitol",
    "ceo",
    "city",
    "committee",
    "company",
    "court",
    "economy",
    "election",
    "federal",
    "government",
    "house",
    "lawmakers",
    "london",
    "market",
    "minister",
    "official",
    "officials",
    "police",
    "president",
    "reuters",
    "report",
    "reported",
    "said",
    "senate",
    "state",
    "supreme",
    "tax",
    "trump",
    "vote",
    "voted",
    "washington",
}


def resolve_db_path():
    configured_path = os.environ.get("DB_PATH")
    if configured_path:
        return configured_path

    render_disk_path = os.path.join("/var/data", "users.db")
    if os.path.isdir("/var/data") or os.path.exists("/var/data"):
        return render_disk_path

    return os.path.join(BASE_DIR, "users.db")


def combine_notices(*messages):
    return " ".join(message for message in messages if message)


def analyze_input(text):
    cleaned = normalize_text(text)
    if not cleaned:
        raise ValueError("Text is empty")

    word_count = len(cleaned.split())
    if word_count < MIN_ANALYSIS_WORDS:
        raise ValueError(f"Input too short. Please paste at least {MIN_ANALYSIS_WORDS} words.")

    notice_parts = []
    if word_count < MIN_RELIABLE_WORDS:
        notice_parts.append("This is a short paragraph, so the result may be less reliable than a full article.")

    if not is_news(cleaned):
        notice_parts.append("This input does not look like a news article, so no real/fake verdict was forced.")
        return "NOT NEWS", None, None, combine_notices(*notice_parts)

    prediction, confidence, explanation = predict_article(cleaned)
    return prediction, confidence, explanation, combine_notices(*notice_parts)

DB_PATH = resolve_db_path()

db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)


@app.route("/test")
def test():
    return "Flask is working perfectly ✅"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


create_table()


def create_history_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            news TEXT,
            prediction TEXT,
            confidence REAL
        )
        """
    )
    conn.commit()
    conn.close()


create_history_table()


@app.route("/")
def home():
    return redirect("/login")


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = generate_password_hash(request.form.get("password", ""))

        conn = None
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password),
            )
            conn.commit()

            # Auto-login only for this first session after registration
            session.clear()
            session["user"] = username
            session["just_registered"] = True
            # ensure prior login flag is not set
            session.pop("via_login", None)
            flash("Registration successful. Welcome!", "success")
            return redirect("/dashboard")

        except sqlite3.IntegrityError:
            flash("User already exists or invalid data.", "error")
            return redirect("/register")

        except Exception:
            flash("Registration error. Please try again.", "error")
            return redirect("/register")

        finally:
            if conn:
                conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect("/admin")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user"] = user["username"]
            # mark this session as an explicit login so future visits remain authenticated
            session["via_login"] = True
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


def normalize_text(text):
    if not text:
        return ""
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_news(text):
    cleaned = normalize_text(text)
    if not cleaned:
        return False

    words = cleaned.split()
    if len(words) < 15:
        return False

    lower = cleaned.lower()
    hits = 0
    for cue in NEWS_CUES:
        if re.search(rf"\b{re.escape(cue)}\b", lower):
            hits += 1

    sentence_count = len([sentence for sentence in re.split(r"[.!?]+", text) if len(sentence.split()) >= 4])
    if hits >= 2:
        return True

    if hits >= 1 and (sentence_count >= 2 or len(words) >= 35):
        return True

    return False


def fetch_article_text(url):
    if not url:
        raise ValueError("No URL provided")

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=15) as response:
        html = response.read().decode("utf-8", errors="ignore")

    cleaned = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned.split()) < 60:
        raise ValueError("The page did not contain enough article text")

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.split()) > 8]
    return " ".join(sentences[:20]) if sentences else cleaned


def compute_features(texts):
    if isinstance(texts, str):
        texts = [texts]
    if vectorizer is None:
        raise RuntimeError("vectorizer.pkl is required for inference")
    return vectorizer.transform(texts)


def predict_article(text):
    cleaned = normalize_text(text)
    if not cleaned:
        raise ValueError("Text is empty")

    data = compute_features([cleaned])
    result = int(model.predict(data)[0])
    probabilities = model.predict_proba(data)[0]
    confidence = round(float(max(probabilities)) * 100, 2)
    prediction = "REAL" if result == 1 else "FAKE"
    # build a lightweight explanation: matched keywords and top words
    lower = cleaned.lower()
    matched = [cue for cue in sorted(NEWS_CUES) if re.search(rf"\b{re.escape(cue)}\b", lower)]
    # top words (simple frequency, excluding common stopwords)
    stop = set(["the","and","a","to","of","in","for","on","is","that","it","with","as","was","are","be","by","an","this","from","at"])
    words = [w for w in re.findall(r"\w+", lower) if w not in stop]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:6]
    top_words = [w for w, _ in top]

    explanation = {"keywords": matched, "top_words": top_words}
    return prediction, confidence, explanation


def get_article_preview(text, limit=120):
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "..."


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    # Must have a user in session AND either be an explicit login session
    # or the one-time just-registered session. Any stale session without
    # these flags will be cleared and required to log in again.
    if "user" not in session:
        return redirect("/login")

    if not session.get("via_login") and not session.get("just_registered") and not session.get("admin"):
        # clear any stale session and require login
        session.clear()
        return redirect("/login")

    prediction = None
    confidence = None
    error = None
    notice = None
    explanation = None
    news_content = ""
    news_url = ""

    if request.method == "POST":
        news_content = (request.form.get("news", "") or "").strip()
        news_url = (request.form.get("url", "") or "").strip()

        try:
            if news_url:
                news_content = fetch_article_text(news_url)
            elif not news_content:
                error = "Please paste article text or provide a valid URL."
            else:
                prediction, confidence, explanation, notice = analyze_input(news_content)
                if prediction in ("REAL", "FAKE"):
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT INTO history (username, news, prediction, confidence) VALUES (?, ?, ?, ?)",
                        (session["user"], news_content[:2000], prediction, confidence),
                    )
                    conn.commit()
                    conn.close()
                    flash("Analysis completed successfully!", "success")
                    # expose explanation to template
        except Exception as exc:
            error = f"Unable to analyze this content: {exc}"

    conn = get_db_connection()
    stats_data = conn.execute(
        "SELECT "
        "COUNT(*) as total, "
        "SUM(CASE WHEN prediction='REAL' THEN 1 ELSE 0 END) as real, "
        "SUM(CASE WHEN prediction='FAKE' THEN 1 ELSE 0 END) as fake "
        "FROM history WHERE username=?",
        (session["user"],),
    ).fetchone()
    conn.close()

    total = stats_data["total"] or 0
    real = stats_data["real"] or 0
    fake = stats_data["fake"] or 0
    accuracy = round((real / total) * 100, 2) if total > 0 else 0

    stats = {"total": total, "real": real, "fake": fake, "accuracy": accuracy}

    preview = get_article_preview(news_content) if news_content else ""

    # If this was the immediate post-registration visit, remove the
    # one-time flag so subsequent visits require the user to log in.
    if session.get("just_registered"):
        session.pop("just_registered", None)

    return render_template(
        "dashboard.html",
        user=session["user"],
        prediction=prediction,
        confidence=confidence,
        error=error,
        notice=notice,
        explanation=explanation,
        stats=stats,
        news_text=news_content,
        news_url=news_url,
        preview=preview,
    )


@app.route("/admin")
def admin():
    if "admin" not in session:
        flash("Unauthorized access!", "error")
        return redirect("/login")

    conn = get_db_connection()
    history_data = conn.execute("SELECT * FROM history ORDER BY id DESC").fetchall()
    users_data = conn.execute("SELECT id, username, email FROM users").fetchall()
    conn.close()

    return render_template("admin.html", history=history_data, users=users_data)


@app.route("/admin/delete_record/<int:record_id>")
def delete_record(record_id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    flash("Record deleted successfully", "info")
    return redirect("/admin")


@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash("User account removed", "info")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return f"Error: {e}", 500
    finally:
        conn.close()

    return redirect("/admin")


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("admin", None)
    session.pop("via_login", None)
    session.pop("just_registered", None)
    return redirect("/login")


@app.route("/predict", methods=["POST"])
def predict():
    user_input = (request.form.get("news", "") or "").strip()
    url_input = (request.form.get("url", "") or "").strip()

    if url_input:
        try:
            user_input = fetch_article_text(url_input)
        except Exception as exc:
            return render_template("dashboard.html", prediction=f"Unable to analyze URL: {exc}")

    if not user_input:
        return render_template("dashboard.html", prediction="⚠ Please paste article text or provide a valid URL.")

    try:
        prediction, confidence, explanation, notice = analyze_input(user_input)
    except ValueError as exc:
        return render_template("dashboard.html", prediction=f"⚠ {exc}")

    return render_template("dashboard.html", prediction=prediction, confidence=confidence, notice=notice)


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    # JSON API for AJAX analysis
    url_input = (request.form.get('url', '') or '').strip()
    user_input = (request.form.get('news', '') or '').strip()
    error = None
    try:
        if url_input:
            user_input = fetch_article_text(url_input)
        if not user_input:
            return {'error': 'Please paste article text or provide a valid URL.'}, 400
        prediction, confidence, explanation, notice = analyze_input(user_input)
        # save history if user present
        if 'user' in session and prediction in ('REAL', 'FAKE'):
            try:
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO history (username, news, prediction, confidence) VALUES (?, ?, ?, ?)",
                    (session['user'], user_input[:2000], prediction, confidence),
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

        return {
            'prediction': prediction,
            'confidence': confidence,
            'explanation': explanation,
            'notice': notice,
            'preview': get_article_preview(user_input)
        }
    except Exception as exc:
        return {'error': f'Unable to analyze this content: {exc}'}, 500


@app.route("/metrics")
def metrics():
    with open("metrics.json") as f:
        data = json.load(f)
    return render_template("metrics.html", accuracy=data["accuracy"])


@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM history WHERE username=? ORDER BY id DESC",
        (session["user"],),
    ).fetchall()
    conn.close()

    return render_template("history.html", records=records)


@app.route("/health")
def health():
    return "I am awake!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)