## 1. 🌐 Endpoint URL

Untuk melakukan prediksi, kirimkan sebuah **POST Request** ke endpoint berikut:

POST `http://localhost:8000/cortia/api/v1/predict`

---

## 2. Penjelasan Request Body (JSON)

API mengharapkan payload JSON dengan struktur *key-value* berikut untuk memproses prediksi:

| Parameter | Tipe Data | Penjelasan |
| :--- | :--- | :--- |
| `daerah` | `string` | ID daerah yang akan diproses. Nilai yang valid sesuai ketersediaan model: `"jakarta_127"`, `"jawa_timur_15"`, atau `"jawa_tengah_42"`. |
| `award_date` | `string` | Tanggal kontrak diberikan dengan format `YYYY-MM-DD`. |
| `tender_minvalue` | `float` | Batas nilai minimum tender atau HPS (Harga Perkiraan Sendiri) dalam Rupiah. |
| `award_value` | `float` | Nilai kontrak akhir yang disepakati dengan pemenang tender dalam Rupiah. |
| `tender_title` | `string` | Judul proyek/tender pada saat pengumuman awal. |
| `award_title` | `string` | Judul kontrak yang disepakati pasca-tender. |
| `award_supplier` | `string` | Nama entitas atau perusahaan pemenang tender. |
| `days_to_award` | `int` | Durasi hari yang dihitung dari awal proses tender hingga penentuan pemenang. |
| `mainprocurementcategory` | `string` | Kategori utama pengadaan barang/jasa (Contoh: `"Goods"`, `"Services"`, atau `"Works"`). |

---

## 3. Penjelasan Response

Jika request berhasil diproses dengan parameter yang benar, API akan mengembalikan respons berformat JSON seperti penjelasan di bawah ini:

| Field | Tipe Data | Penjelasan |
| :--- | :--- | :--- |
| `status` | `string` | Status proses HTTP (mengembalikan `"success"` jika data berhasil diproses). |
| `daerah_diproses` | `string` | ID daerah yang digunakan oleh sistem untuk memuat model prediksi. |
| `score` | `float` | Skor anomali numerik yang dihasilkan oleh model *Isolation Forest*. Semakin tinggi angkanya, semakin tinggi indikasi anomali. |
| `risk_level` | `string` | Klasifikasi tingkat risiko dari transaksi tersebut (`"low"`, `"medium"`, atau `"high"`). |
| `human_readable_explanation`| `string` | Penjelasan komprehensif dalam bahasa natural dari Chatbot yang menjelaskan alasan di balik penetapan tingkat risiko, berdasarkan kontribusi fitur (SHAP values). |

**Contoh Format Response:**
```json
{
  "status": "success",
  "daerah_diproses": "jakarta_127",
  "score": 0.4125,
  "risk_level": "low",
  "human_readable_explanation": "[LOW] Status transaksi dinilai AMAN dan memenuhi kriteria kepatuhan standar:\n• Parameter Laju Pengeluaran Harian sangat identik dengan profil pengadaan...\n• Parameter Kompleksitas Judul Kontrak menunjukkan aktivitas yang dinamis namun tetap sesuai dengan standar operasional.\n• Meskipun terdapat temuan risiko lain, parameter Batas Minimum Tender terpantau tetap stabil."
}

---

## 4. Contoh JSON

**JAKARTA**
{
  "daerah": "jakarta_127",
  "award_date": "2023-04-14",
  "tender_minvalue": 1252306428.2,
  "award_value": 1145627700.0,
  "tender_title": "Jasa Eo Pemilihan Abang Dan None Jakarta Selatan Tahun 2023",
  "award_title": "Jasa Eo Pemilihan Abang Dan None Jakarta Selatan Tahun 2023",
  "award_supplier": "Pt. Ishana Abyakta Indonesia",
  "days_to_award": 11,
  "mainprocurementcategory": "Services"
}

**JAWA TENGAH**

{
  "daerah": "jawa_tengah_42",
  "award_date": "2023-05-23",
  "tender_minvalue": 774999780.0,
  "award_value": 692862000.0,
  "tender_title": "Dd Penanganan Banjir Dan Rob Kab. Kendal",
  "award_title": "Dd Penanganan Banjir Dan Rob Kab. Kendal",
  "award_supplier": "Primasetia Eng Con",
  "days_to_award": 47,
  "mainprocurementcategory": "Services"
}

**JAWA TIMUR**

{
  "daerah": "jawa_timur_15",
  "award_date": "2017-09-29",
  "tender_minvalue": 895950000.0,
  "award_value": 876150000.0,
  "tender_title": "Belanja Modal Pengadaan Alat-Alat Kedokteran Nebulizer",
  "award_title": "Belanja Modal Pengadaan Alat-Alat Kedokteran Nebulizer",
  "award_supplier": "Anggada Jaya",
  "days_to_award": 11,
  "mainprocurementcategory": "Goods"
}