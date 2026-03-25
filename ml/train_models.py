import os
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score

# Insert project root so ml.data_generator resolves correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.data_generator import (
    generate_credit_dataset,
    generate_fraud_dataset,
    generate_late_payment_dataset,
)

MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')
os.makedirs(MODELS_PATH, exist_ok=True)


# ── 1. Credit Scoring (Logistic Regression) ────────────────────────────────────
def train_credit_model():
    print("\n[1/4] Training Credit Scoring Model (Logistic Regression)...")
    df = generate_credit_dataset(10000)
    features = [
        'age', 'monthly_income', 'employment_type', 'existing_bnpl_count',
        'past_defaults', 'avg_transaction_amount', 'payment_history_score',
        'kyc_verified', 'account_age_days'
    ]
    X = df[features]
    y = df['approved']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = LogisticRegression(random_state=42, max_iter=1000, C=1.0)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)

    acc = accuracy_score(y_test, y_pred)
    print(f"   Accuracy : {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['Rejected', 'Approved']))

    joblib.dump(model,    os.path.join(MODELS_PATH, 'credit_model.pkl'))
    joblib.dump(scaler,   os.path.join(MODELS_PATH, 'credit_scaler.pkl'))
    joblib.dump(features, os.path.join(MODELS_PATH, 'credit_features.pkl'))
    print("   ✓ Credit model saved.")
    return acc


# ── 2. Fraud Detection (Isolation Forest + Random Forest) ─────────────────────
def train_fraud_model():
    print("\n[2/4] Training Fraud Detection Models (IsolationForest + RandomForest)...")
    df = generate_fraud_dataset(10000)
    features = [
        'transaction_amount', 'transaction_hour', 'transactions_last_24h',
        'amount_vs_avg_ratio', 'location_change_flag', 'device_change_flag',
        'velocity_score', 'ip_risk_score'
    ]
    X = df[features]
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Handle class imbalance — try SMOTE, fall back gracefully
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_train_r, y_train_r = smote.fit_resample(X_train, y_train)
        print("   SMOTE applied for class balancing.")
    except Exception as e:
        print(f"   SMOTE skipped ({e}). Using original distribution.")
        X_train_r, y_train_r = X_train.copy(), y_train.copy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train_r)
    X_test_s  = scaler.transform(X_test)

    # Isolation Forest — anomaly detection
    iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    iso.fit(X_train_s)

    # Random Forest — supervised fraud probability
    rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    rf.fit(X_train_s, y_train_r)
    y_pred = rf.predict(X_test_s)

    acc = accuracy_score(y_test, y_pred)
    print(f"   RF Accuracy : {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))

    joblib.dump(iso,      os.path.join(MODELS_PATH, 'fraud_isolation_forest.pkl'))
    joblib.dump(rf,       os.path.join(MODELS_PATH, 'fraud_rf_model.pkl'))
    joblib.dump(scaler,   os.path.join(MODELS_PATH, 'fraud_scaler.pkl'))
    joblib.dump(features, os.path.join(MODELS_PATH, 'fraud_features.pkl'))
    print("   ✓ Fraud models saved.")
    return acc


# ── 3. Late Payment Prediction (Random Forest) ────────────────────────────────
def train_late_payment_model():
    print("\n[3/4] Training Late Payment Prediction Model (Random Forest)...")
    df = generate_late_payment_dataset(10000)
    features = [
        'days_since_last_payment', 'missed_payments_count', 'income_to_emi_ratio',
        'spending_volatility', 'salary_day_proximity', 'active_loans_count'
    ]
    X = df[features]
    y = df['will_pay_late']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_train_r, y_train_r = smote.fit_resample(X_train, y_train)
    except Exception as e:
        print(f"   SMOTE skipped ({e}).")
        X_train_r, y_train_r = X_train.copy(), y_train.copy()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train_r)
    X_test_s  = scaler.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=100, random_state=42, class_weight='balanced'
    )
    model.fit(X_train_s, y_train_r)
    y_pred = model.predict(X_test_s)

    acc = accuracy_score(y_test, y_pred)
    print(f"   Accuracy : {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['On Time', 'Late']))

    joblib.dump(model,    os.path.join(MODELS_PATH, 'late_payment_model.pkl'))
    joblib.dump(scaler,   os.path.join(MODELS_PATH, 'late_payment_scaler.pkl'))
    joblib.dump(features, os.path.join(MODELS_PATH, 'late_payment_features.pkl'))
    print("   ✓ Late payment model saved.")
    return acc


# ── 4. EMI Optimizer (KNN + Decision Tree) ────────────────────────────────────
def train_emi_optimizer():
    print("\n[4/4] Training EMI Optimizer (KNN + Decision Tree)...")
    np.random.seed(42)
    n = 5000
    credit_scores    = np.random.randint(300, 900, n)
    monthly_incomes  = np.random.randint(10000, 200000, n)
    past_defaults    = np.random.randint(0, 4, n)
    existing_loans   = np.random.randint(0, 5, n)

    recommended_tenure = []
    for i in range(n):
        if credit_scores[i] >= 750 and past_defaults[i] == 0:
            tenure = 9
        elif credit_scores[i] >= 650:
            tenure = 6
        else:
            tenure = 3
        recommended_tenure.append(tenure)

    df = pd.DataFrame({
        'credit_score':       credit_scores,
        'monthly_income':     monthly_incomes,
        'past_defaults':      past_defaults,
        'existing_loans':     existing_loans,
        'recommended_tenure': recommended_tenure
    })
    features = ['credit_score', 'monthly_income', 'past_defaults', 'existing_loans']
    X = df[features]
    y = df['recommended_tenure']

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(X_s, y)
    knn_acc = accuracy_score(y, knn.predict(X_s))

    dt = DecisionTreeClassifier(random_state=42, max_depth=5)
    dt.fit(X_s, y)
    dt_acc = accuracy_score(y, dt.predict(X_s))

    print(f"   KNN train accuracy : {knn_acc:.4f}")
    print(f"   DT  train accuracy : {dt_acc:.4f}")

    joblib.dump(knn,      os.path.join(MODELS_PATH, 'emi_knn_model.pkl'))
    joblib.dump(dt,       os.path.join(MODELS_PATH, 'emi_dt_model.pkl'))
    joblib.dump(scaler,   os.path.join(MODELS_PATH, 'emi_scaler.pkl'))
    joblib.dump(features, os.path.join(MODELS_PATH, 'emi_features.pkl'))
    print("   ✓ EMI optimizer models saved.")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  SmartPay ML Model Training Pipeline")
    print("=" * 55)

    results = {}
    results['credit']       = train_credit_model()
    results['fraud']        = train_fraud_model()
    results['late_payment'] = train_late_payment_model()
    train_emi_optimizer()

    print("\n" + "=" * 55)
    print("  TRAINING COMPLETE — Summary")
    print("=" * 55)
    for name, acc in results.items():
        print(f"  {name:<20} accuracy = {acc:.4f} ({acc*100:.2f}%)")
    print(f"\n  Models saved → {MODELS_PATH}")
    print("=" * 55)
