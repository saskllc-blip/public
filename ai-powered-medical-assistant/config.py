"""Global configuration — loads .env and defines all shared constants."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_DIR        = os.path.join(BASE_DIR, "data")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")
LOGS_DIR        = os.path.join(BASE_DIR, "logs")
for _d in [DATA_DIR, VECTORSTORE_DIR, LOGS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ── Data files ────────────────────────────────────────────────────────────────
PATIENTS_FILE       = os.path.join(DATA_DIR, "patients.json")
DOCTORS_FILE        = os.path.join(DATA_DIR, "doctors.json")
APPOINTMENTS_FILE   = os.path.join(DATA_DIR, "appointments.json")
MEDICAL_RECORDS_FILE = os.path.join(DATA_DIR, "medical_records.json")
VISIT_HISTORY_FILE  = os.path.join(DATA_DIR, "visit_history.json")  # past visits + labs (generated)
TOOL_LOGS_FILE      = os.path.join(LOGS_DIR, "tool_logs.json")
EVAL_LOGS_FILE      = os.path.join(LOGS_DIR, "eval_logs.json")
AGENT_TRACES_FILE   = os.path.join(LOGS_DIR, "agent_traces.json")

# ── Medical Vault ─────────────────────────────────────────────────────────────
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ── Agent ─────────────────────────────────────────────────────────────────────
MAX_ITERATIONS = 10
MEMORY_WINDOW  = 5

# ── RAG ───────────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 3

# ── Evaluation ────────────────────────────────────────────────────────────────
EVAL_SAMPLE_SIZE = 5

# ── UI ────────────────────────────────────────────────────────────────────────
APP_TITLE   = "🏥 AI-Powered Healthcare Assistant"
APP_ICON    = "🏥"
THEME_COLOR = "#1E88E5"
