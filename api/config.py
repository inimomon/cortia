import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Path Konfigurasi
    BASE_DIR = Path(__file__).resolve().parent.parent
    ARTIFACT_DIR = BASE_DIR / "artifacts" / "post_award_anomaly" / "by_daerah"
    
    # Daftar Daerah
    DAERAH_LIST = ["jakarta_127", "jawa_timur_15", "jawa_tengah_42"]
    
    # Database Konfigurasi
    DB_CONFIG = {
        'host': os.getenv("DB_HOST", "localhost"),
        'user': os.getenv("DB_USER", "root"),
        'password': os.getenv("DB_PASSWORD", ""),
        'database': os.getenv("DB_NAME", "cortia_db")
    }