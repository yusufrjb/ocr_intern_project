# 📄 OCR Intern Project

Proyek ini bertujuan untuk mengekstrak data dari tagihan PLN berbentuk PDF dan menyimpannya ke dalam database PostgreSQL menggunakan Flask sebagai backend API.

## 🚀 Fitur
- Upload satu atau banyak file PDF.
- Ekstraksi data otomatis dengan PyMuPDF (fitz).
- Penyimpanan ke PostgreSQL dengan pengecekan duplikat.
- Cek struktur dan validasi data PDF.

## 📂 Struktur Folder
```bash
ocr_intern_project/
├── app.py # Flask backend
├── extract_pln.py # Fungsi ekstraksi PDF
├── uploads/ # Tempat penyimpanan file PDF sementara
├── .env # Konfigurasi database
├── requirements.txt # Daftar dependensi Python
└── README.md # Dokumentasi proyek
```

## ⚙️ Setup
```bash
### 1. Install dependensi
pip install -r requirements.txt

### 2. Atur konfigurasi database .env
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

### 3. Jalankan backend Flask
python app.py


```

### 🗂️ `uploads/`

> Buat folder kosong bernama `uploads` di root direktori:

```bash
mkdir uploads
