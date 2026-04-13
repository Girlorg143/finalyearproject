# AGRI SUPPLY CHAIN - INSTALLATION & EXECUTION GUIDE

---

## TABLE OF CONTENTS
1. System Requirements
2. Software Installation
3. Package Installation
4. Environment Configuration
5. Database Setup
6. Execution Sequence
7. Deployment (Render)

---

## 1. SYSTEM REQUIREMENTS

### Minimum Requirements
- **OS**: Windows 10/11, Linux, or macOS
- **Python**: 3.9 or higher
- **RAM**: 4 GB minimum (8 GB recommended)
- **Storage**: 2 GB free space
- **Browser**: Chrome/Firefox/Edge (latest version)

### Optional (For AI Features)
- **GPU**: 4GB VRAM (for local LLM)
- **LLM Server**: 8GB additional RAM

---

## 2. SOFTWARE INSTALLATION

### Step 1: Install Python
1. Download Python 3.9+ from https://www.python.org/downloads/
2. During installation, **check "Add Python to PATH"**
3. Verify installation:
   ```bash
   python --version
   pip --version
   ```

### Step 2: Install Git
1. Download from https://git-scm.com/download/win
2. Choose "Use Git from the command line" during setup
3. Verify:
   ```bash
   git --version
   ```

### Step 3: Install VS Code (Recommended)
1. Download from https://code.visualstudio.com/
2. Install extensions:
   - Python
   - Pylance
   - Auto Rename Tag
   - Prettier

### Step 4: Install PostgreSQL (Optional - for production)
1. Download from https://www.postgresql.org/download/
2. Set password for `postgres` user
3. Default port: 5432

---

## 3. PACKAGE INSTALLATION

### Step 1: Navigate to Project Directory
```bash
cd e:\final_yr1\final_yr1\final_yr1\final_yr
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify (should show "(venv)" prefix)
```

### Step 3: Install Python Packages
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### Key Packages Installed:
| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 2.3.3 | Web framework |
| Flask-SQLAlchemy | 3.0.5 | ORM for database |
| Flask-JWT-Extended | 4.5.2 | JWT authentication |
| Flask-Migrate | 4.0.4 | Database migrations |
| Flask-CORS | 4.0.0 | Cross-origin requests |
| psycopg2-binary | 2.9.7 | PostgreSQL driver |
| pandas | 2.0.3 | Data processing |
| numpy | 1.24.3 | Numerical operations |
| scikit-learn | 1.3.0 | Machine learning |
| requests | 2.31.0 | HTTP requests |
| python-dotenv | 1.0.0 | Environment variables |
| Werkzeug | 2.3.7 | WSGI utilities |
| Gunicorn | 21.2.0 | Production server |
| llama-cpp-python | 0.2.11 | Local LLM support |
| openai | 1.2.0 | OpenAI API |

---

## 4. ENVIRONMENT CONFIGURATION

### Step 1: Create Environment File
Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/agri_supply_chain
# Or for SQLite (development): sqlite:///agri_supply_chain.db

# Security
JWT_SECRET_KEY=your-super-secret-key-change-this
SECRET_KEY=another-secret-key-for-flask

# API Keys
OPENWEATHER_API_KEY=your_openweather_api_key
TOMTOM_API_KEY=your_tomtom_api_key
OPENAI_API_KEY=your_openai_key_optional

# Server Configuration
PORT=5004
FLASK_ENV=development
FLASK_DEBUG=1

# LLM Configuration (Optional)
LLAMA_SERVER_URL=http://localhost:8080
GENAI_USE_OPENAI=false
GENAI_WAREHOUSE_USE_LLM=false
```

### Step 2: Database Initialization (First Time)
```bash
# Create database tables
flask db init      # Only first time
flask db migrate   # Create migration
flask db upgrade   # Apply migration
```

---

## 5. EXECUTION SEQUENCE

### SEQUENCE 1: LOCAL DEVELOPMENT (Full Features)

#### Terminal 1: Start Backend Server
```powershell
# Navigate to backend
$env:PORT=5004
python backend/app.py
```
**Output**: Server running on http://localhost:5004

#### Terminal 2: Start LLM Server (Optional)
```powershell
# Download llama.cpp server first
# From: https://github.com/ggerganov/llama.cpp/releases

# Start local LLM
E:\llama\llama-server.exe -m E:\llama\models\mistral.gguf --port 8080
```
**Output**: LLM server running on http://localhost:8080

#### Terminal 3: Open Frontend
```bash
# Open in browser directly
start http://localhost:5004

# Or open HTML file
start frontend/index.html
```

**Access URLs:**
- Frontend: http://localhost:5004
- Backend API: http://localhost:5004/api
- Admin Panel: http://localhost:5004/admin

---



---

### SEQUENCE 3: PRODUCTION DEPLOYMENT (Render)

#### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/agri-supply-chain.git
git push -u origin main
```

#### Step 2: Create Render Account
1. Sign up at https://render.com
2. Create New Web Service
3. Connect GitHub repository

#### Step 3: Configure Render Environment
```bash
# Build Command
pip install -r requirements.txt

# Start Command
gunicorn --bind 0.0.0.0:$PORT backend.app:app

# Environment Variables
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
SECRET_KEY=...
PORT=10000
GENAI_USE_OPENAI=false
LLAMA_SERVER_URL=  # Empty for fallback mode
```

#### Step 4: Deploy
Click "Create Web Service" - automatic deployment begins

**Access URL**: https://agri-supply-chain.onrender.com

---

## 6. FILE EXECUTION ORDER

### Project Structure
```
agri_supply_chain/
├── backend/
│   ├── app.py              # Entry point - RUN FIRST
│   ├── config.py           # Configuration loaded
│   ├── models.py           # Database models
│   ├── routes/
│   │   ├── farmer.py       # Farmer API routes
│   │   ├── warehouse.py    # Warehouse API routes
│   │   ├── logistics.py    # Logistics API routes
│   │   └── admin.py        # Admin API routes
│   └── services/
│       ├── genai.py        # AI recommendations
│       ├── weather.py      # Weather API
│       └── ml.py           # ML predictions
├── frontend/
│   ├── index.html          # Main entry
│   ├── static/
│   │   ├── css/           # Stylesheets
│   │   └── js/            # JavaScript files
│   └── templates/         # HTML templates
├── agri_supply_chain_datasets/
│   └── crop_freshness_shelf_life_seasonal_corrected.csv
├── requirements.txt       # Dependencies
└── .env                  # Environment variables
```

### Execution Flow
```
1. User opens browser → frontend/index.html
2. Frontend calls API → backend/app.py
3. App initializes → config.py, models.py
4. API routes handle → routes/*.py
5. Services process → services/*.py
6. Database operations → models.py → SQLite/PostgreSQL
7. Response returned → JSON to frontend
8. Frontend displays → Updates UI
```

---

## 7. TROUBLESHOOTING

### Common Issues

**Issue**: `ModuleNotFoundError`
**Fix**: `pip install -r requirements.txt`

**Issue**: `Port already in use`
**Fix**: Change port: `$env:PORT=5005`

**Issue**: `Database locked`
**Fix**: Close other Python instances, use PostgreSQL

**Issue**: `LLM server not found`
**Fix**: Set `LLAMA_SERVER_URL=` (empty) to use fallback

---

## 8. VERIFICATION CHECKLIST

Before using the system, verify:

- [ ] Python 3.9+ installed
- [ ] Virtual environment activated
- [ ] All packages installed (pip list)
- [ ] .env file created with keys
- [ ] Database initialized (flask db upgrade)
- [ ] Backend server running (no errors)
- [ ] Frontend accessible in browser
- [ ] Login page loads
- [ ] Can create farmer account
- [ ] Can submit crop batch

---

## QUICK START COMMANDS

```bash
# 1. Setup (One time)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env with your keys

# 3. Database
flask db upgrade

# 4. Run
$env:PORT=5004
python backend/app.py

# 5. Open
start http://localhost:5004
```

---

**System Ready!** 🚀
