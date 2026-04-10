## 1. Endpoint URL

API menyediakan dua endpoint inference utama:

- `POST http://localhost:8000/cortia/api/v1/predict_input_text`
- `POST http://localhost:8000/cortia/api/v1/predict_file`

Untuk kompatibilitas demo lama, endpoint berikut juga tetap didukung dan setara dengan endpoint JSON:

- `POST http://localhost:8000/cortia/api/v1/predict`

---

## 2. Penjelasan Request Body JSON

Endpoint `predict_input_text` mengharapkan payload JSON dengan struktur berikut:

| Parameter | Tipe Data | Penjelasan |
| :--- | :--- | :--- |
| `daerah` | `string` | ID daerah yang akan diproses. Nilai valid: `"jakarta_127"`, `"jawa_timur_15"`, atau `"jawa_tengah_42"`. |
| `award_date` | `string` | Tanggal kontrak dengan format `YYYY-MM-DD`. |
| `tender_minvalue` | `float` | Batas nilai minimum tender atau HPS dalam Rupiah. |
| `award_value` | `float` | Nilai kontrak akhir yang disepakati dengan pemenang tender. |
| `tender_title` | `string` | Judul proyek atau tender pada saat pengumuman awal. |
| `award_title` | `string` | Judul kontrak yang disepakati pasca-tender. |
| `award_supplier` | `string` | Nama entitas atau perusahaan pemenang tender. |
| `days_to_award` | `int` | Durasi hari dari awal proses tender sampai penentuan pemenang. |
| `mainprocurementcategory` | `string` | Kategori utama pengadaan, misalnya `"Goods"`, `"Services"`, atau `"Works"`. |

---

## 3. Penjelasan Response JSON

Jika request berhasil diproses, API mengembalikan respons seperti berikut:

| Field | Tipe Data | Penjelasan |
| :--- | :--- | :--- |
| `status` | `string` | Status proses HTTP, bernilai `"success"` bila prediksi berhasil. |
| `daerah_diproses` | `string` | ID daerah yang dipakai untuk memuat model prediksi. |
| `score` | `float` | Skor anomali dari model `IsolationForest`. Semakin tinggi, semakin kuat indikasi anomali. |
| `risk_percentage` | `float` | Persentase risiko 0-100 yang diturunkan dari skor anomali terhadap threshold model. |
| `risk_level` | `string` | Tingkat risiko transaksi: `"low"`, `"medium"`, atau `"high"`. |
| `human_readable_explanation` | `string` | Penjelasan naratif berbasis kontribusi fitur SHAP. |

Contoh response:

```json
{
  "status": "success",
  "daerah_diproses": "jakarta_127",
  "score": 0.4125,
  "risk_percentage": 0.0,
  "risk_level": "low",
  "human_readable_explanation": "[LOW] Status transaksi dinilai AMAN dan memenuhi kriteria kepatuhan standar:\n• Parameter Laju Pengeluaran Harian sangat identik dengan profil pengadaan...\n• Parameter Kompleksitas Judul Kontrak menunjukkan aktivitas yang dinamis namun tetap sesuai dengan standar operasional.\n• Meskipun terdapat temuan risiko lain, parameter Batas Minimum Tender terpantau tetap stabil."
}
```

---

## 4. Contoh JSON untuk `predict_input_text`

**JAKARTA**

```json
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
```

**JAWA TENGAH**

```json
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
```

**JAWA TIMUR**

```json
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
```

---

## 5. Penjelasan Endpoint `predict_file`

Endpoint `predict_file` menerima:

- file CSV melalui field `file`
- ID daerah melalui field form-data `daerah`

CSV minimal harus memiliki kolom berikut:

- `award_date`
- `tender_minvalue`
- `award_value`
- `tender_title`
- `award_title`
- `award_supplier`
- `days_to_award`
- `mainprocurementcategory`

Response endpoint file berisi ringkasan jumlah data yang diproses dan daftar hasil prediksi untuk tiap baris.
