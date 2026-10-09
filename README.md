# 📰 News Authenticity Classifier

[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Render-green?style=for-the-badge&logo=render)](https://news-detector-hbx6.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI%20Powered-orange?style=for-the-badge&logo=google)](https://ai.google.dev/)

A full-stack Machine Learning application that detects fake news articles with high precision. Combines a trained **NLP classifier** with a **live AI scanner** powered by Google Gemini — giving you two ways to verify any news story in real-time.

---

## 🚀 Live Demo
**Check it out here:** [https://news-detector-hbx6.onrender.com](https://news-detector-hbx6.onrender.com)
> ⚠️ Hosted on Render's free tier — the first load may take ~50 seconds to "wake up" the server.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **News Detection** | Instant fake/real prediction using a Passive Aggressive Classifier trained on 40K+ articles |
| ⚡ **Current News Detection** | Fetches current news via GNews API and evaluates credibility with Google Gemini |
| 📊 **Dashboard & Stats** | Personalized prediction history with an interactive Chart.js donut chart |
| 🔐 **Secure Auth** | Full Login/Registration with bcrypt-hashed passwords |
| 👤 **Admin Panel** | Manage users, view all predictions, and delete records |
| 📱 **Responsive UI** | Modern, mobile-friendly design built with vanilla CSS |
| 🔔 **Toast Notifications** | Non-intrusive result alerts via Toastify |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Flask 3.1 (Python) |
| **ML Model** | Scikit-learn — Passive Aggressive Classifier |
| **NLP** | TF-IDF Vectorization |
| **AI Analysis** | Google Gemini (via `google-genai` SDK) |
| **News Feed** | GNews API |
| **Database** | SQLite3 |
| **Frontend** | HTML5, Vanilla CSS, JavaScript, Chart.js |
| **Deployment** | Render (Gunicorn) |

---

## ⚙️ Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/news-authenticity-classifier.git
cd news-authenticity-classifier
```

### 2. Create a virtual environment & install dependencies
```bash
python -m venv .venv
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

### 3. Configure API Keys
Create a `.env` file in the project root (never commit this file):

```env
GNEWS_API_KEY
GEMINI_API_KEY
```

| Key | Where to get it |
|---|---|
| `GNEWS_API_KEY` | [gnews.io](https://gnews.io) — free tier available |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) — free |

### 4. Run the app
```bash
python app.py
```
Visit **http://127.0.0.1:5000** in your browser.

---

## 💾 Persistent Storage on Render

SQLite is configurable via the `DB_PATH` environment variable.

For permanent storage on Render, attach a disk and set `DB_PATH` to a path like `/var/data/users.db`. If `DB_PATH` is unset, the app checks for a Render disk at `/var/data/` and falls back to the local project folder.

---

## 📊 Model Performance

| Metric | Value |
|---|---|
| **Accuracy** | 98.46% |
| **Algorithm** | Passive Aggressive Classifier + TF-IDF |
| **Training Data** | ~40,000 labelled news articles |
| **Status** | ✅ Verified & Deployed |

---

## 📂 Project Structure

```text
news-authenticity-classifier/
├── app.py                  # Main Flask application & routes
├── news_pipeline.py        # GNews fetch + Gemini AI analysis module
├── train_model.py          # ML training script
├── model.pkl               # Trained classifier (Passive Aggressive)
├── vectorizer.pkl          # Fitted TF-IDF vectorizer
├── requirements.txt        # Python dependencies
├── .env                    # API keys — create locally, do NOT commit
├── static/
│   └── style.css           # Global design system
├── templates/
│   ├── base.html           # Shared layout (navbar, scripts)
│   ├── dashboard.html      # User dashboard (NLP + Live AI tabs)
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── history.html        # Prediction history
│   ├── admin.html          # Admin panel
│   └── how_it_works.html   # How It Works page
├── tests/
│   ├── test_app_logic.py   # Flask route & NLP logic tests
│   └── test_news_pipeline.py  # GNews + Gemini pipeline tests
└── dataset/                # Training CSV data (not uploaded to GitHub)
```

---

## 🧪 Running Tests

```bash
python -m unittest discover tests
```

All 19 tests should pass (app logic + news pipeline).

---

## 🔑 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `GNEWS_API_KEY` | ❌ Optional | GNews API key; Google News RSS is used when it is unavailable |
| `GEMINI_API_KEY` | ❌ Optional | Google Gemini API key; the local classifier is used when it is unavailable |
| `DB_PATH` | ❌ Optional | Custom path for SQLite database |
| `PORT` | ❌ Optional | Server port (default: `5000`) |
