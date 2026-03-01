import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import json

print("Loading dataset...")
# Load dataset
fake = pd.read_csv("dataset/Fake.csv")
true = pd.read_csv("dataset/True.csv")

fake["label"] = 0
true["label"] = 1

df = pd.concat([fake, true])
df = df[["text", "label"]]

# To get a real accuracy score, we split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(df["text"], df["label"], test_size=0.2, random_state=42)

print("Vectorizing text...")
vectorizer = TfidfVectorizer(stop_words="english", max_df=0.7)
# Use fit_transform on training data
X_train_vec = vectorizer.fit_transform(X_train)
# Use transform on test data
X_test_vec = vectorizer.transform(X_test)

print("Training model...")
model = LogisticRegression()
model.fit(X_train_vec, y_train)

print("Calculating accuracy...")
y_pred = model.predict(X_test_vec)
accuracy = accuracy_score(y_test, y_pred)
print(f"✅ Accuracy: {round(accuracy * 100, 2)}%")

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