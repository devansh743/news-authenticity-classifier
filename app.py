from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import pickle
import os
import json

ADMIN_EMAIL = "admin@fnd.com"
ADMIN_PASSWORD = "admin123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model = pickle.load(open(os.path.join(BASE_DIR, "model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, "vectorizer.pkl"), "rb"))
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secretkey123"

# Absolute path for database (WINDOWS FIX)
DB_PATH = os.path.join(BASE_DIR, "users.db")

# ---------- TEST ROUTE ----------
@app.route("/test")
def test():
    return "Flask is working perfectly ✅"

# ---------- DATABASE ----------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

create_table()

def create_history_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            news TEXT,
            prediction TEXT,
            confidence REAL
        )
    """)
    conn.commit()
    conn.close()

create_history_table()

# ---------- ROUTES ----------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
            conn.close()

            flash("Registration successful. Please login.", "success")
            return redirect("/login")

        except Exception:
            flash("User already exists or invalid data.", "error")
            return redirect("/register")

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # ✅ ADMIN LOGIN
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session['admin'] = True
            return redirect('/admin')

        # ✅ USER LOGIN
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user'] = user['username']
            return redirect('/dashboard')
        else:
            return render_template(
                'login.html',
                error="Invalid email or password"
            )

    # ✅ VERY IMPORTANT (GET request)
    return render_template('login.html')


# ---------- UPDATED DASHBOARD ROUTE ----------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    prediction = None
    confidence = None
    error = None
    news_content = ""

    if request.method == "POST":
        news_content = request.form.get("news", "")

        # 1. Basic Validation
        if not news_content or len(news_content.strip()) < 100:
            error = "Article too short. Please paste at least 100 characters."
        
        # 2. Heuristic Check (is_news)
        elif not is_news(news_content):
            error = "This doesn't look like a news article. Please provide factual content."
        
        else:
            try:
                # ML Prediction
                data = vectorizer.transform([news_content])
                result = model.predict(data)[0]
                prob = model.predict_proba(data)[0]

                confidence = round(max(prob) * 100, 2)
                prediction = "REAL" if result == 1 else "FAKE"

                # Save to History
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO history (username, news, prediction, confidence) VALUES (?, ?, ?, ?)",
                    (session["user"], news_content[:500], prediction, confidence)
                )
                conn.commit()
                conn.close()
                flash("Analysis completed successfully!", "success")
            except Exception as e:
                error = "Analysis failed. Please try again later."

    # Fetch Stats for the UI
    conn = get_db_connection()
    stats_data = conn.execute(
        "SELECT "
        "COUNT(*) as total, "
        "SUM(CASE WHEN prediction='REAL' THEN 1 ELSE 0 END) as real, "
        "SUM(CASE WHEN prediction='FAKE' THEN 1 ELSE 0 END) as fake "
        "FROM history WHERE username=?", (session["user"],)
    ).fetchone()

    total = stats_data['total'] or 0
    real = stats_data['real'] or 0
    fake = stats_data['fake'] or 0
    accuracy = round((real / total) * 100, 2) if total > 0 else 0
    conn.close()

    stats = {
        "total": total,
        "real": real,
        "fake": fake,
        "accuracy": accuracy
    }

    return render_template(
        "dashboard.html",
        user=session["user"],
        prediction=prediction,
        confidence=confidence,
        error=error,
        stats=stats,
        news_text=news_content # Returns the text to the textarea if there's an error
    )

# DELETE the old @app.route('/predict') entirely!


@app.route('/admin')
def admin():
    if 'admin' not in session:
        flash("Unauthorized access!", "error")
        return redirect('/login')

    conn = get_db_connection()
    # Fetch all history and all users for full control
    history_data = conn.execute("SELECT * FROM history ORDER BY id DESC").fetchall()
    users_data = conn.execute("SELECT id, username, email FROM users").fetchall()
    conn.close()

    return render_template('admin.html', history=history_data, users=users_data)

@app.route('/admin/delete_record/<int:record_id>')
def delete_record(record_id):
    if 'admin' not in session: return redirect('/login')
    
    conn = get_db_connection()
    conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    flash("Record deleted successfully", "info")
    return redirect('/admin')

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'admin' not in session: return redirect('/login')
    
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User account removed", "info")
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('admin', None)
    return redirect('/login')

def is_news(text):
    # Rule 1: Minimum length check
    if len(text.split()) < 20:
        return False

    # Rule 2: Check for news-like keywords
    news_keywords = ["said", "reported", "government", "minister",
                     "police", "announced", "according", "election"]

    for word in news_keywords:
        if word in text.lower():
            return True

    return False

@app.route('/predict', methods=['POST'])
def predict():
    user_input = request.form['news']

    # 🔹 Check if input is news
    if not is_news(user_input):
        return render_template("dashboard.html",
                               prediction="⚠ This does not appear to be a news article.")

    # 🔹 If it is news → Continue Fake/Real prediction
    transformed_input = vectorizer.transform([user_input])
    prediction = model.predict(transformed_input)

    if prediction[0] == 0:
        result = "📰 This is Real News"
    else:
        result = "🚨 This is Fake News"

    return render_template("dashboard.html", prediction=result)

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
        (session["user"],)
    ).fetchall()
    conn.close()

    return render_template("history.html", records=records)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",   # Explicit localhost binding (FIX)
        port=5000
    )