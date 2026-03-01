# 📰 News Authenticity Classifier

[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Render-green?style=for-the-badge&logo=render)](https://news-detector-hbx6.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)

A full-stack Machine Learning application that detects fake news articles with high precision. This project uses Natural Language Processing (NLP) to analyze text patterns and classify them as **Real** or **Fake** in real-time.

---

## 🚀 Live Demo
**Check it out here:** [https://news-detector-hbx6.onrender.com](https://news-detector-hbx6.onrender.com)  
*(Note: As it is hosted on Render's free tier, the first load may take ~50 seconds to "wake up" the server.)*

---

## ✨ Features
- **Real-time Detection:** Instant analysis of news snippets using AI.
- **User Dashboard:** Personalized history of all your news checks.
- **Visualization:** Interactive donut charts (Chart.js) showing prediction confidence.
- **Secure Auth:** Full Login/Registration system with encrypted passwords.
- **Admin Panel:** Special access to manage users and monitor system performance.
- **Responsive UI:** Modern, mobile-friendly design.

---

## 🛠 Tech Stack
- **Backend:** Flask (Python)
- **Machine Learning:** Scikit-learn (Passive Aggressive Classifier)
- **NLP:** TF-IDF Vectorization
- **Database:** SQLite3
- **Frontend:** HTML5, CSS3 (Modern Flexbox), JavaScript, Chart.js
- **Deployment:** Render (Production-grade with Gunicorn)

---

## 📊 Model Performance
The model was trained on a balanced dataset of ~40,000 news articles.
- **Accuracy:** ~94.5% 
- **Algorithm:** Passive Aggressive Classifier
- **Preprocessing:** Stop-word removal & TF-IDF Vectorization

---

## 📂 Project Structure
```text
news-authenticity-classifier/
│── app.py              # Main Flask application
│── train_model.py      # ML training script
│── model.pkl           # Saved AI model
│── vectorizer.pkl      # Saved TF-IDF vectorizer
│── requirements.txt    # Project dependencies
│── static/             # CSS, Images, and JS files
│── templates/          # HTML files (Dashboard, Login, etc.)
└── dataset/            # CSV data (not uploaded to GitHub)
