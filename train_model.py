import json
import pickle

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

# Use a lightweight sentence-transformers model to avoid large CPU memory use
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

print("Loading dataset...")
fake = pd.read_csv("dataset/Fake.csv")
true = pd.read_csv("dataset/True.csv")

fake["label"] = 0
true["label"] = 1

df = pd.concat([fake, true], ignore_index=True)
df = df[["text", "label"]].copy()
df["text"] = df["text"].fillna("").astype(str)
df["text"] = df["text"].str.replace(r"\s+", " ", regex=True).str.strip()

X_train, X_test, y_train, y_test = train_test_split(
    df["text"],
    df["label"],
    test_size=0.2,
    random_state=42,
    stratify=df["label"],
)

print("Loading sentence-transformer model (small, memory efficient)...")
st_model = SentenceTransformer(MODEL_NAME)


def compute_embeddings(texts, batch_size=64):
    # SentenceTransformer handles batching and converts to numpy directly
    return st_model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)


print("Computing embeddings...")
X_train_emb = compute_embeddings(X_train.tolist(), batch_size=64)
X_test_emb = compute_embeddings(X_test.tolist(), batch_size=64)

print("Training model...")
model = LogisticRegression(max_iter=2000, class_weight="balanced")
model.fit(X_train_emb, y_train)

print("Calculating accuracy...")
y_pred = model.predict(X_test_emb)
accuracy = accuracy_score(y_test, y_pred)
print(f"✅ Accuracy: {round(accuracy * 100, 2)}%")

print("Saving model file...")
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("metrics.json", "w") as f:
    json.dump({"accuracy": round(accuracy * 100, 2)}, f)

print("✅ Training complete. Files saved successfully.")