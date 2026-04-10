from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, Form, File, BackgroundTasks
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib
import json
import io
import mysql.connector
from datetime import datetime
from config import Config

# --- KONFIGURASI APP ---
app = FastAPI(
    title="Cortia Anomaly Detection API",
    description="API untuk mendeteksi anomali pengadaan barang/jasa menggunakan Isolation Forest & SHAP Explainer. Data tersimpan otomatis ke MySQL.",
    version="1.1.0"
)
router = APIRouter(prefix="/cortia/api/v1")

# --- LOAD ARTIFACTS (MODEL ML) ---
models_db = {}

print(f"Mencari model di: {Config.ARTIFACT_DIR}")
print("Memuat model ke dalam memori...")
for d in Config.DAERAH_LIST:
    reg_dir = Config.ARTIFACT_DIR / d
    if reg_dir.exists():
        models_db[d] = {
            "model": joblib.load(reg_dir / "isolation_forest.joblib"),
            "preprocessor": joblib.load(reg_dir / "preprocessor.joblib"),
            "explainer_shap": joblib.load(reg_dir / "shap_explainer.joblib"),
            "model_config": json.loads((reg_dir / "model_config.json").read_text(encoding="utf-8")),
            "explanation_meta": json.loads((reg_dir / "explanation_meta.json").read_text(encoding="utf-8"))
        }
        print(f"Model {d} berhasil diload.")
    else:
        print(f"Peringatan: Folder {reg_dir} tidak ditemukan.")

# --- DATA MODELS (UNTUK SWAGGER DOKUMENTASI) ---
class ProcurementData(BaseModel):
    daerah: str = Field(..., example="jakarta_127", description="ID Daerah (jakarta_127, jawa_timur_15, dll)")
    award_date: str = Field(..., example="2023-05-20", description="Format: YYYY-MM-DD")
    tender_minvalue: float = Field(..., example=1500000000.0)
    award_value: float = Field(..., example=1495000000.0)
    tender_title: str = Field(..., example="Pembangunan Jembatan Beton")
    award_title: str = Field(..., example="Kontrak Pembangunan Jembatan")
    award_supplier: str = Field(..., example="PT. Bangun Sejahtera, PT. Maju Jaya")
    days_to_award: int = Field(..., example=5)
    mainprocurementcategory: str = Field(..., example="Works")

# --- KAMUS MAPPING UNTUK SHAP (PENJELASAN) ---
KAMUS_KONSEP = {
    "award_title_word_count": "Kompleksitas Judul Kontrak",
    "days_to_award": "Durasi Proses Tender",
    "budget_utilization_ratio": "Rasio Penyerapan Anggaran",
    "value_gap": "Selisih Nilai Tender dan Kontrak",
    "supplier_count": "Jumlah Peserta Tender",
    "award_value_per_day": "Laju Pengeluaran Harian",
    "tender_minvalue": "Batas Minimum Tender",
    "award_value": "Nilai Kontrak Akhir"
}

KAMUS_RISIKO = {
    "award_title_word_count": "pola penamaan judul yang tidak standar seringkali digunakan untuk mengaburkan spesifikasi asli proyek.",
    "days_to_award": "proses yang selesai terlalu cepat atau terlalu lambat mengindikasikan adanya potensi pengaturan pemenang (bid-rigging).",
    "budget_utilization_ratio": "penyerapan yang mendekati 100% secara sempurna merupakan indikator umum terjadinya mark-up harga.",
    "value_gap": "selisih yang tidak proporsional menunjukkan potensi inefisiensi atau kesalahan estimasi biaya awal.",
    "supplier_count": "minimnya partisipan tender dapat mengurangi kompetisi sehat dan meningkatkan risiko monopoli.",
    "award_value_per_day": "beban biaya harian yang ekstrem menunjukkan ketidakwajaran antara nilai proyek dengan durasi pengerjaan.",
    "tender_minvalue": "penetapan batas minimum yang tidak lazim berisiko membatasi partisipasi vendor kompeten."
}

# --- DATABASE FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(**Config.DB_CONFIG)

def save_prediction_to_db(daerah, tender_title, score, risk_level, explanation):
    """Menyimpan satu prediksi ke tabel MySQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO predictions 
            (daerah, tender_title, score, risk_level, explanation, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (daerah, tender_title, score, risk_level, explanation, datetime.now())
        
        cursor.execute(query, values)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"❌ Error Database: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def save_batch_predictions_to_db(daerah, results):
    """Menyimpan banyak prediksi sekaligus ke tabel MySQL."""
    if not results: return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO predictions 
            (daerah, tender_title, score, risk_level, explanation, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        data_to_insert = [
            (daerah, r['tender_title'], r['score'], r['risk_level'], r['human_readable_explanation'], datetime.now())
            for r in results
        ]
        
        cursor.executemany(query, data_to_insert)
        conn.commit()
        print(f"✅ Berhasil menyimpan {len(results)} data dari file CSV ke MySQL.")
    except mysql.connector.Error as err:
        print(f"❌ Error Database Batch: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# --- LOGIC HELPER FUNCTIONS ---
def format_number(value):
    if pd.isna(value): return "missing"
    if isinstance(value, (int, np.integer)): return f"{int(value):,}"
    if isinstance(value, (float, np.floating)): return f"{value:,.2f}"
    return str(value)

def engineer_features(frame):
    data = frame.copy()
    data["award_date"] = pd.to_datetime(data["award_date"])
    data["award_month"] = data["award_date"].dt.month
    data["award_quarter"] = data["award_date"].dt.quarter
    data["award_weekday"] = data["award_date"].dt.weekday
    data["log_tender_minvalue"] = np.log1p(data["tender_minvalue"])
    data["log_award_value"] = np.log1p(data["award_value"])
    data["value_gap"] = data["award_value"] - data["tender_minvalue"]
    data["budget_utilization_ratio"] = data["award_value"] / data["tender_minvalue"].replace(0, np.nan)
    data["budget_utilization_ratio"] = data["budget_utilization_ratio"].fillna(0)
    data["title_word_count"] = data["tender_title"].fillna("").str.split().str.len()
    data["award_title_word_count"] = data["award_title"].fillna("").str.split().str.len()
    data["supplier_count"] = data["award_supplier"].fillna("").astype(str).str.split(",").str.len()
    data["award_value_per_day"] = data["award_value"] / data["days_to_award"].replace(0, 1)
    data["same_day_award_flag"] = (data["days_to_award"] == 0).astype(int)
    return data

def assign_severity(scores, medium_cutoff, anomaly_threshold):
    return np.select(
        [scores >= anomaly_threshold, scores >= medium_cutoff],
        ["high", "medium"],
        default="low"
    )[0]

def calculate_risk_percentage(score, medium_cutoff, anomaly_threshold):
    """Convert the anomaly score into an intuitive 0-100 risk percentage."""
    denominator = max(float(anomaly_threshold) - float(medium_cutoff), 1e-9)
    raw_percentage = ((float(score) - float(medium_cutoff)) / denominator) * 100
    return round(float(np.clip(raw_percentage, 0, 100)), 2)

def normalize_shap_values(shap_values):
    """Handle SHAP return shapes across library versions."""
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    if getattr(shap_values, "ndim", 1) > 1:
        return shap_values[0]
    return shap_values

def get_raw_feature_value(original_row, feature_name):
    raw_feature_name = "mainprocurementcategory" if feature_name.startswith("cat_") else feature_name
    raw_value = original_row[raw_feature_name] if raw_feature_name in original_row else "N/A"
    return raw_feature_name, raw_value

def generate_natural_reason(feat, raw_val, shap_val, severity_band):
    is_anomaly_driver = shap_val > 0
    nama_manusiawi = KAMUS_KONSEP.get(feat, feat.replace("_", " ").title())
    val_str = format_number(raw_val)
    
    if severity_band == "high":
        if is_anomaly_driver:
            risiko = KAMUS_RISIKO.get(feat, "hal ini memerlukan verifikasi kepatuhan dokumen lebih lanjut.")
            return f"Sistem menemukan indikasi penyimpangan serius pada **{nama_manusiawi}** ({val_str}). Secara audit, {risiko}"
        return f"Meskipun terdapat temuan risiko lain, parameter **{nama_manusiawi}** ({val_str}) terpantau tetap stabil."
    elif severity_band == "medium":
        if is_anomaly_driver:
            return f"Terdapat sedikit kejanggalan pada data **{nama_manusiawi}** ({val_str}). Meskipun menunjukkan pola yang tidak biasa, angka ini dinilai masih berada dalam batas toleransi kebijakan."
        return f"Parameter **{nama_manusiawi}** ({val_str}) memberikan sinyal kestabilan di tengah beberapa anomali minor lainnya."
    else:
        if is_anomaly_driver:
            return f"Komponen **{nama_manusiawi}** ({val_str}) menunjukkan aktivitas yang dinamis namun tetap sesuai dengan standar operasional."
        return f"Parameter **{nama_manusiawi}** ({val_str}) sangat identik dengan profil pengadaan yang bersih dan akuntabel."

def explain_prediction_shap(original_row, row_shap, explanation_meta):
    feature_names = explanation_meta["feature_names_preprocessed"]
    severity_band = original_row['severity_band']
    top_indices = np.argsort(np.abs(row_shap))[-3:][::-1]
    
    reasons = []
    for idx in top_indices:
        feat_name = feature_names[idx]
        raw_feat_name, raw_val = get_raw_feature_value(original_row, feat_name)
        reasons.append(generate_natural_reason(raw_feat_name, raw_val, row_shap[idx], severity_band))
    
    if severity_band == "high": header = "Sistem mendeteksi aktivitas yang MENCURIGAKAN dan berisiko tinggi:"
    elif severity_band == "medium": header = "Sistem menemukan beberapa temuan BORDERLINE yang memerlukan perhatian moderat:"
    else: header = "Status transaksi dinilai AMAN dan memenuhi kriteria kepatuhan standar:"

    return f"[{severity_band.upper()}] {header}\n" + "\n".join([f"• {r}" for r in reasons])

# --- ENDPOINTS ---
@router.get("/", tags=["Health Check"])
def read_root():
    return {"status": "online", "message": "Welcome to Cortia API v1!", "database": "Terhubung jika DB aktif"}

@router.post("/predict", tags=["Inference"], include_in_schema=False)
@router.post("/predict_input_text", tags=["Inference"])
def predict_anomaly(payload: ProcurementData, background_tasks: BackgroundTasks):
    daerah = payload.daerah
    if daerah not in models_db:
        raise HTTPException(status_code=400, detail=f"Daerah '{daerah}' tidak ditemukan.")
    
    target_artifacts = models_db[daerah]
    model = target_artifacts["model"]
    preprocessor = target_artifacts["preprocessor"]
    explainer_shap = target_artifacts["explainer_shap"]
    model_config = target_artifacts["model_config"]
    explanation_meta = target_artifacts["explanation_meta"]
    
    feature_columns = model_config["numeric_features"] + model_config["categorical_features"]

    payload_dict = payload.model_dump()
    payload_dict.pop('daerah')
    demo_input = pd.DataFrame([payload_dict])
    
    demo_features = engineer_features(demo_input)
    X_demo = preprocessor.transform(demo_features[feature_columns])
    demo_score = float(-model.score_samples(X_demo)[0])
    risk_percentage = calculate_risk_percentage(
        demo_score,
        model_config["medium_cutoff"],
        model_config["anomaly_threshold"]
    )
    
    severity_band = assign_severity(
        np.array([demo_score]), 
        model_config["medium_cutoff"], 
        model_config["anomaly_threshold"]
    )
    demo_features["severity_band"] = severity_band
    
    shap_values = normalize_shap_values(explainer_shap.shap_values(X_demo))
    explanation = explain_prediction_shap(demo_features.iloc[0], shap_values, explanation_meta)
    
    # Simpan ke Database
    background_tasks.add_task(
        save_prediction_to_db, 
        daerah, payload.tender_title, round(demo_score, 4), severity_band, explanation
    )
    
    return {
        "status": "success",
        "daerah_diproses": daerah,
        "score": round(demo_score, 4),
        "risk_percentage": risk_percentage,
        "risk_level": severity_band,
        "human_readable_explanation": explanation
    }


@router.post("/predict_file", tags=["Inference"])
async def predict_anomaly_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Upload file CSV berisikan data pengadaan"),
    daerah: str = Form(..., description="ID Daerah (contoh: jawa_timur_15)")
):
    if daerah not in models_db:
        raise HTTPException(status_code=400, detail=f"Daerah '{daerah}' tidak ditemukan.")
    
    try:
        contents = await file.read()
        df_input = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file CSV. Error: {str(e)}")
        
    required_columns = [
        "award_date", "tender_minvalue", "award_value", "tender_title",
        "award_title", "award_supplier", "days_to_award", "mainprocurementcategory"
    ]
    missing_cols = [col for col in required_columns if col not in df_input.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"CSV tidak valid! Kehilangan kolom: {', '.join(missing_cols)}")
        
    target_artifacts = models_db[daerah]
    model = target_artifacts["model"]
    preprocessor = target_artifacts["preprocessor"]
    explainer_shap = target_artifacts["explainer_shap"]
    model_config = target_artifacts["model_config"]
    explanation_meta = target_artifacts["explanation_meta"]
    
    feature_columns = model_config["numeric_features"] + model_config["categorical_features"]
    
    demo_features = engineer_features(df_input)
    X_demo = preprocessor.transform(demo_features[feature_columns])
    demo_scores = -model.score_samples(X_demo)
    
    severity_bands = [
        assign_severity(np.array([s]), model_config["medium_cutoff"], model_config["anomaly_threshold"]) 
        for s in demo_scores
    ]
    risk_percentages = [
        calculate_risk_percentage(s, model_config["medium_cutoff"], model_config["anomaly_threshold"])
        for s in demo_scores
    ]
    demo_features["severity_band"] = severity_bands
    
    shap_values_batch = explainer_shap.shap_values(X_demo)
    if isinstance(shap_values_batch, list):
        shap_values_batch = shap_values_batch[0]
        
    results = []
    for i in range(len(df_input)):
        raw_score = float(demo_scores[i])
        explanation = explain_prediction_shap(demo_features.iloc[i], shap_values_batch[i], explanation_meta)
        
        results.append({
            "baris_ke": i + 1,
            "tender_title": str(df_input.iloc[i].get("tender_title", "Unknown")),
            "score": round(raw_score, 4),
            "risk_percentage": risk_percentages[i],
            "risk_level": severity_bands[i],
            "human_readable_explanation": explanation
        })
        
    # Simpan data batch ke database berjalan di background 
    background_tasks.add_task(save_batch_predictions_to_db, daerah, results)
        
    return {
        "status": "success",
        "daerah_diproses": daerah,
        "total_data_diproses": len(results),
        "data": results
    }

app.include_router(router)
