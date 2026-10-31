# Larteh Lingo (Gua Language Engine) 🇬🇭

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stack: Flask + React](https://img.shields.io/badge/Stack-Flask%20%7C%20React%20%7C%20PostgreSQL-blue)](https://github.com/)

**Larteh Lingo** is an open-source digital preservation engine and community learning platform for **Larteh (Gua)**—a native West African language spoken in the Akuapem ridge of the Eastern Region of Ghana.

The mission of this platform is two-fold:
1. **Cultural Preservation:** Provide native speakers and the global Ghanaian diaspora with an accessible, mobile-first Progressive Web App (PWA) to record, document, and preserve authentic pronunciations, numbers, days, and oral heritage.
2. **Speech AI & Dataset Infrastructure:** Collect structured phonetic alignments and lossless voice recordings formatted as open datasets for automatic speech recognition (ASR), translation models, and linguistic research.

---

## 🏛️ System Architecture

```text
┌─────────────────────────────────┐
│       React 18 PWA (Vite)       │  <-- Browser MediaRecorder API
│  (Mobile Audio Recorder + Form) │  <-- Virtual Orthographic Keyboard (ɛ, ɔ, ɲ)
└────────────────┬────────────────┘
                 │
                 │ HTTP / REST (/api/v1) [Multipart Audio + JSON]
                 ▼
┌─────────────────────────────────┐
│     Flask Application Engine    │  <-- SQLAlchemy 2.0 ORM
│       (Python 3.11+ WSGI)       │  <-- Marshmallow & Werkzeug Validators
└────────┬────────────────────────┘
         │
         ├───▶ [ PostgreSQL 16 ]  <-- Taxonomic Categories & Lexicon Entries
         │
         └───▶ [ S3 / Cloudflare R2 / Local Storage ]
               (Lossless .wav / .webm Audio Archive)
```

---

## 📂 Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Flask Application Factory with CORS & Blueprints
│   │   ├── config.py             # 12-factor configuration (Dev, Test, Prod)
│   │   ├── extensions.py         # SQLAlchemy, Migrate, CORS singletons
│   │   ├── models/
│   │   │   ├── category.py       # Category model with auto-slugification
│   │   │   └── lexicon.py        # LexiconEntry model with UUID & GrammaticalType
│   │   ├── routes/
│   │   │   ├── categories.py     # GET /categories, POST /categories
│   │   │   └── lexicon.py        # GET /lexicon (filters), POST /lexicon/upload
│   │   ├── services/
│   │   │   └── storage.py        # AWS S3 / Cloudflare R2 / Local fallback engine
│   │   └── utils/
│   │       └── validators.py     # Audio mimetype & file extension validation
│   ├── tests/                    # Pytest integration test suite
│   ├── seeds.py                  # Days of the Week & Numbers 1–40 seed script
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile
│   └── run.py                    # Local server runner
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── AudioRecorderForm.jsx  # PWA Voice recorder & metadata form
│   │   ├── services/
│   │   │   └── api.js                 # API REST client
│   │   ├── App.jsx                    # Navigation, Explorer & Recorder tabs
│   │   ├── main.jsx
│   │   └── index.css                  # Tailwind styles & waveform keyframes
│   ├── public/manifest.json           # Web App Manifest for mobile PWA
│   ├── tailwind.config.js
│   ├── vite.config.js
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml                 # Orchestration for PostgreSQL, API & Frontend
└── README.md
```

---

## 🗄️ Database Schema

### 1. `Category` (`categories`)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Autoincrement | Category identifier |
| `name` | String(100) | Unique, Not Null | Category name (e.g., "Days of the Week") |
| `slug` | String(120) | Unique, Indexed, Not Null | URL slug (e.g., "days-of-the-week") |
| `description` | Text | Nullable | Explanatory notes |
| `created_at` | DateTime(tz) | Not Null, Default NOW() | Timestamp |

### 2. `LexiconEntry` (`lexicon_entries`)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PK, Default uuid4 | Unique entry identifier |
| `category_id` | Integer | FK `categories.id`, Indexed | Associated taxonomic category |
| `larteh_text` | String(255) | Indexed, Not Null | Larteh orthography (e.g., "Ekɔ", "Epwɛ") |
| `phonetic_script`| String(255) | Not Null | IPA / phonetic script (e.g., "[e-kɔ]") |
| `english_translation` | String(255) | Indexed, Not Null | English translation (e.g., "One (1)") |
| `grammatical_type`| String(50) | Indexed, Not Null | `noun`, `verb`, `cardinal_number`, `day_of_week`, etc. |
| `audio_url` | String(1024)| Nullable | S3 / R2 or local media endpoint |
| `speaker_name` | String(100) | Not Null, Default 'Dad' | Native speaker attribution |
| `cultural_notes`| Text | Nullable | Usage context, folklore, and etymology |
| `created_at` | DateTime(tz) | Not Null, Default NOW() | Timestamp |

---

## 🚀 Quick Start Guide

### Option 1: Docker Compose (Recommended)

Run the complete multi-container stack (PostgreSQL + Flask + React):

```bash
docker compose up --build
```
- Frontend PWA: `http://localhost:80`
- Flask REST API: `http://localhost:5000`
- PostgreSQL: `localhost:5432`

---

### Option 2: Local Development Setup

#### 1. Backend Setup (Flask & PostgreSQL)

```bash
# Navigate to backend
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env to set DATABASE_URL (or leave unset for SQLite development mode)

# Run idempotent database seeding (creates tables, Days of Week, Numbers 1–40)
python seeds.py

# Start Flask development server
python run.py
```
Backend API will be running on `http://localhost:5000`.

#### 2. Frontend Setup (React 18 PWA)

```bash
# In a separate terminal, navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend will be available at `http://localhost:5173`.

---

## 📡 REST API Endpoints (`/api/v1`)

### 1. Categories
- **`GET /api/v1/categories`**: Lists all categories with entry counts.
- **`POST /api/v1/categories`**: Creates a new category.
  ```json
  {
    "name": "Kinship & Family",
    "description": "Terms for relatives and elders."
  }
  ```

### 2. Lexicon
- **`GET /api/v1/lexicon`**: Queries entries with filtering and pagination.
  - Query parameters:
    - `q`: Global search across Larteh, phonetics, and English
    - `larteh_text`: Substring match on Larteh spelling
    - `english_translation`: Substring match on English meaning
    - `category_id`: Category foreign key filter
    - `grammatical_type`: `cardinal_number`, `day_of_week`, `noun`, etc.
    - `page` & `per_page`: Pagination controls

- **`POST /api/v1/lexicon/upload`**: Ingests new lexical record with optional audio blob.
  - Accepts `multipart/form-data`:
    - `audio`: Audio file blob (`.webm`, `.wav`, `.mp3`)
    - `larteh_text`: (Required) String
    - `phonetic_script`: (Required) String (e.g. `[e-kɔ]`)
    - `english_translation`: (Required) String
    - `category_id`: (Optional) Integer ID
    - `grammatical_type`: (Optional) String
    - `speaker_name`: (Optional, defaults to `"Dad"`)
    - `cultural_notes`: (Optional) String

---

## 🎙️ Audio Recording & PWA Features

The React frontend includes:
- **`MediaRecorder` API Stream**: Encodes high-clarity voice audio using `audio/webm;codecs=opus` or lossless `audio/wav`.
- **Live Visual Equalizer**: Real-time feedback during recording sessions.
- **Microphone Controls**: Record, Pause, Resume, Stop, Preview, and Re-record.
- **Phonetic Virtual Keys**: Instant insertion for Ghanaian phonetic symbols (`ɛ`, `ɔ`, `ŋ`, `ɲ`, `ʋ`, `ɖ`, `kp`, `gb`) on mobile touchscreens.
- **Cloud Object Storage Adapter**: Uploads directly to AWS S3 or Cloudflare R2 with automatic fallback to local storage during offline testing.

---

## 🇬🇭 Pre-Populated Seed Data (`seeds.py`)

Running `python seeds.py` populates:
1. **The 7 Days of the Week**:
   - `Idu` (`[i-du]`, Sunday)
   - `Isum` (`[i-sum]`, Monday)
   - `Epwɛ` (`[e-pwɛ]`, Tuesday)
   - `Isu` (`[i-su]`, Wednesday)
   - `Ibiro` (`[i-bi-ro]`, Thursday)
   - `Ife` (`[i-fe]`, Friday)
   - `Yinke` (`[jin-ke]`, Saturday)

2. **Numbers 1 to 40 in Larteh**:
   - 1–10: `Ekɔ`, `Enyɔ`, `Esa`, `Enɛ`, `Enu`, `Esien`, `Esono`, `Etwie`, `Ekpuno`, `Edu`
   - 11–19: `Edu n'Ekɔ`, `Edu n'Enyɔ`, ..., `Edu n'Ekpuno`
   - 20–29: `Aduanyɔ`, `Aduanyɔ n'Ekɔ`, ..., `Aduanyɔ n'Ekpuno`
   - 30–39: `Aduasa`, `Aduasa n'Ekɔ`, ..., `Aduasa n'Ekpuno`
   - 40: `Eduenɛ`

---

## 🧪 Testing

Run automated backend tests using pytest:

```bash
cd backend
pytest -v
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
