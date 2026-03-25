# SmartPay – BNPL Platform

A full-stack **Buy Now, Pay Later** fintech platform with ML-powered credit scoring, fraud detection, and EMI optimisation.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0, Flask-SQLAlchemy, Flask-Login |
| Database | PostgreSQL (psycopg2-binary) |
| ML | scikit-learn, pandas, numpy, imbalanced-learn |
| Server | Gunicorn (production), Flask dev server (local) |
| Deployment | Railway.app |

---

## Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/BNPL_Final.git
cd BNPL_Final
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (never commit this file):

```env
SECRET_KEY=your-very-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/smartpay
UPLOAD_FOLDER=uploads
ML_MODELS_PATH=ml/models
```

### 5. Initialise the database
```bash
# db.create_all() runs automatically on first app start
python app.py
```

### 6. Run the development server
```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

---

## Production Deployment on Railway.app

### Prerequisites
- A [Railway.app](https://railway.app) account
- A GitHub repository with this code pushed to it

### Step-by-step

1. **Create a new Railway project** → *Deploy from GitHub repo*
2. **Add a PostgreSQL plugin** inside the project (Railway provisions it automatically)
3. **Set environment variables** in Railway → Variables tab:

   | Variable | Value |
   |----------|-------|
   | `SECRET_KEY` | A long random string |
   | `DATABASE_URL` | Auto-provided by Railway's Postgres plugin |
   | `UPLOAD_FOLDER` | `uploads` |
   | `ML_MODELS_PATH` | `ml/models` |
   | `FLASK_ENV` | `production` |

4. **Deploy** – Railway detects `Procfile` and runs:
   ```
   web: gunicorn app:application
   ```
5. Railway injects the `PORT` environment variable automatically; the app reads it and binds accordingly.

### Key production files

| File | Purpose |
|------|---------|
| `Procfile` | Tells Railway to start with Gunicorn |
| `runtime.txt` | Pins Python 3.11.0 |
| `requirements.txt` | All dependencies including `gunicorn` |
| `.gitignore` | Keeps secrets and compiled files out of git |

---

## Project Structure

```
BNPL_Final/
├── app.py               # App factory + Gunicorn entry point
├── config.py            # Configuration classes
├── extensions.py        # Flask extensions (db, login_manager, bcrypt)
├── models/              # SQLAlchemy models
├── routes/              # Blueprint route handlers
│   ├── auth.py
│   ├── dashboard.py
│   ├── shop.py
│   ├── bnpl.py
│   ├── admin.py
│   └── api.py
├── ml/                  # Machine learning modules
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, JS, images
├── Procfile             # Railway/Heroku process file
├── runtime.txt          # Python version pin
├── requirements.txt     # Python dependencies
└── .gitignore
```

---

## ML Features

- **Credit Scoring** – Logistic regression / gradient boosting on user financial history
- **Fraud Detection** – Anomaly detection on transaction patterns (Isolation Forest)
- **Late Payment Prediction** – Random Forest default-risk scoring
- **EMI Optimisation** – KNN + Decision Tree ensemble for optimal repayment schedules
- **KYC** – OpenCV liveness detection for deepfake-proof identity verification

---

## License

MIT © SmartPay Team
