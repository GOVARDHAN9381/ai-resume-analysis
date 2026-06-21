import os
import sqlite3
import pickle
import json
import time
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

try:
    from src.nlp_utils import clean_text
except ModuleNotFoundError:
    from nlp_utils import clean_text

def train_models():
    # Make sure output directories exist
    os.makedirs("models", exist_ok=True)
    
    db_path = "data/candidates.db"
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Run data_generator.py first.")
        
    print("Reading data from candidates database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT category, resume_text FROM candidates")
    rows = cursor.fetchall()
    conn.close()
    
    print(f"Loaded {len(rows)} resume records.")
    
    categories = [row[0] for row in rows]
    resumes = [row[1] for row in rows]
    
    print("Preprocessing resume texts (this may take a few seconds)...")
    start_time = time.time()
    cleaned_resumes = [clean_text(r) for r in resumes]
    print(f"Preprocessing completed in {time.time() - start_time:.2f} seconds.")
    
    # Vectorization
    print("Extracting TF-IDF features...")
    vectorizer = TfidfVectorizer(max_features=1500)
    X = vectorizer.fit_transform(cleaned_resumes)
    y = categories
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training shape: {X_train.shape}, Testing shape: {X_test.shape}")
    
    # 1. Train Random Forest
    print("Training Random Forest Classifier...")
    rf_start = time.time()
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    rf_time = time.time() - rf_start
    print(f"Random Forest trained in {rf_time:.2f} seconds.")
    
    # 2. Train Gradient Boosting
    print("Training Gradient Boosting Classifier...")
    gb_start = time.time()
    # Using HistGradientBoostingClassifier or lower estimators/depth for faster local training
    # HistGradientBoostingClassifier is fast but requires dense input or specific setup.
    # GradientBoostingClassifier with n_estimators=50 is fast and standard.
    gb_model = GradientBoostingClassifier(n_estimators=50, learning_rate=0.1, max_depth=3, random_state=42)
    gb_model.fit(X_train.toarray(), y_train) # GB works on dense matrix easily for 50 estimators
    gb_time = time.time() - gb_start
    print(f"Gradient Boosting trained in {gb_time:.2f} seconds.")
    
    # Evaluate Random Forest
    rf_preds = rf_model.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_preds)
    rf_report = classification_report(y_test, rf_preds, output_dict=True)
    rf_cm = confusion_matrix(y_test, rf_preds).tolist()
    print(f"Random Forest Test Accuracy: {rf_acc:.4f}")
    
    # Evaluate Gradient Boosting
    gb_preds = gb_model.predict(X_test.toarray())
    gb_acc = accuracy_score(y_test, gb_preds)
    gb_report = classification_report(y_test, gb_preds, output_dict=True)
    gb_cm = confusion_matrix(y_test, gb_preds).tolist()
    print(f"Gradient Boosting Test Accuracy: {gb_acc:.4f}")
    
    # Save the models and vectorizer
    print("Saving trained models and vectorizer...")
    with open("models/vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
        
    with open("models/random_forest_model.pkl", "wb") as f:
        pickle.dump(rf_model, f)
        
    with open("models/gradient_boosting_model.pkl", "wb") as f:
        pickle.dump(gb_model, f)
        
    # Unique categories list
    unique_categories = sorted(list(set(y)))
    
    # Save metrics JSON
    metrics = {
        "rf": {
            "accuracy": rf_acc,
            "train_time_seconds": rf_time,
            "report": rf_report,
            "confusion_matrix": rf_cm
        },
        "gb": {
            "accuracy": gb_acc,
            "train_time_seconds": gb_time,
            "report": gb_report,
            "confusion_matrix": gb_cm
        },
        "categories": unique_categories
    }
    
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    print("Model training and saving completed successfully!")

if __name__ == "__main__":
    train_models()
