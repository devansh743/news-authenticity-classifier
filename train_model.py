import pandas as pd
import pickle
import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import json

print("Loading dataset...")

# Load dataset (local CSV)
fake = pd.read_csv("dataset/Fake.csv")
true = pd.read_csv("dataset/True.csv")

fake["label"] = 0
true["label"] = 1

df = pd.concat([fake, true])
df = df[["text", "label"]]

X = df["text"]
y = df["label"]

print("Vectorizing text...")
vectorizer = TfidfVectorizer(stop_words="english", max_df=0.7)
X_vec = vectorizer.fit_transform(X)
y_pred = model.predict(X)
accuracy = accuracy_score(y, y_pred)

print("Training model...")
model = LogisticRegression()
model.fit(X_vec, y)

print("Saving model files...")
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

with open("metrics.json", "w") as f:
    json.dump({
        "accuracy": round(accuracy * 100, 2)
    }, f)

print("✅ Training complete. Files saved successfully.")
