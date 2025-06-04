import os
import psycopg2
from flask import Flask, request, jsonify
from extract_pln import extract_pdf_info_fitz
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pandas as pd
import numpy as np

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')                                                                                                                                                       

load_dotenv(dotenv_path)  


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
 
@app.route('/')
def index():
    return "✅ Backend berjalan", 200

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    files = request.files.getlist('file')
    responses = []

    for file in files:
        if file.filename == '':
            responses.append({'filename': None, 'error': 'No selected file'})
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = None
        cur = None
        try:
            df = extract_pdf_info_fitz(filepath)
            thbl = df.at[0, "THBL"]
            id_pel = df.at[0, "ID Pelanggan"]

            if not thbl or not id_pel:
                responses.append({'filename': filename, 'error': 'Data tidak lengkap'})
                continue
            
            # Validasi hasil ekstraksi
            if thbl in [None, "", "Tidak ditemukan"] or id_pel in [None, "", "Tidak ditemukan"]:
                responses.append({
                    'filename': filename,
                    'error': '[❌] File tidak valid atau tidak sesuai format'
                })
                continue

            conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PWD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT", 5432)
            )
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM tagihan_pln WHERE thbl = %s AND id_pelanggan = %s", (thbl, id_pel))
            if cur.fetchone():
                responses.append({'filename': filename, 'error': 'Data duplikat'})
                continue

            columns = [
                "Nama File", "THBL", "No Rekening", "ID Pelanggan", "Nama Pelanggan",
                "Alamat Pelanggan", "Nama Sesuai NPWP", "Alamat Sesuai NPWP", "Status", "Golongan Tarif",
                "Faktor Kali Meter", "NIK", "Subsidi", "kWh LWBP", "kWh WBP", "kVArh",
                "Tarif LWBP", "Tarif WBP", "Tarif kVArh", "Jatuh Tempo", "Tunggakan Bulan Sebelumnya",
                "BP (Biaya Penyambungan)", "UJL (Uang Jaminan Langganan)", "Angsuran Lainnya", "Biaya Beban / EMIN", "Total Tagihan",
                "Rupiah TTL Terpakai", "Rupiah Kompensasi", "Rupiah TTL minus Kompensasi", "DPP", "PPN",
                "PBJT-TL", "Rupiah Jasa Layanan dan Keandalan, sewa trafo, paralel, dll Inc. Tax",
                "Renewable Energy Certificate", "PPN Renewable Energy Certificate"
            ]

            row = df.loc[0, columns]

            insert_query = """
                INSERT INTO tagihan_pln (
                    nama_file, thbl, no_rekening, id_pelanggan, nama_pelanggan,
                    alamat_pelanggan, nama_npwp, alamat_npwp, status, golongan_tarif,
                    faktor_kali_meter, nik, subsidi, kwh_lwbp, kwh_wbp, kvarh,
                    tarif_lwbp, tarif_wbp, tarif_kvarh, jatuh_tempo, tunggakan_sebelumnya,
                    biaya_penyambungan, ujl, angsuran_lain, biaya_beban, total_tagihan, rupiah_terpakai,
                    rupiah_kompensasi, rupiah_setelah_kompensasi, dpp, ppn, pbjt, jasa_layanan,
                    rec, ppn_rec
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            """

            values = row[0:35].tolist()

            def convert_value(x):
                if pd.isna(x):
                    return None
                if isinstance(x, (np.generic,)):
                    return x.item()
                return x

            values = [convert_value(v) for v in values]

            cur.execute(insert_query, tuple(values))
            conn.commit()

            responses.append({'filename': filename, 'message': '✅ Data berhasil disimpan'})

        except Exception as e:
            import traceback
            traceback.print_exc()
            responses.append({'filename': filename, 'error': str(e)})

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return jsonify(responses), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
