import os
import fitz  # PyMuPDF
import pandas as pd
import re
from datetime import datetime

def clean_thbl(thbl_str):
    try:
        return datetime.strptime(thbl_str, "%m-%Y").strftime("%Y-%m-01")
    except:
        return "Tidak ditemukan"  

def clean_jatuh_tempo(tgl_str):
    try:
        # Handle "20 Mei 2025" → "2025-05-20"
        bulan_map = {
            # Bahasa Indonesia
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05",
            "Juni": "06", "Juli": "07", "Agustus": "08", "September": "09",
            "Oktober": "10", "November": "11", "Desember": "12",

            # English
            "January": "01", "February": "02", "March": "03", "April": "04", "May": "05",
            "June": "06", "July": "07", "August": "08", "September": "09",
            "October": "10", "November": "11", "December": "12"
        }
        match = re.match(r"(\d{1,2}) (\w+) (\d{4})", tgl_str)
        if match:
            day, month_str, year = match.groups()
            month = bulan_map.get(month_str)
            if month:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass
    return "Tidak ditemukan"

def extract_pdf_info_fitz(file_path):
    with fitz.open(file_path) as doc:
        text = "\n".join([page.get_text("text", sort=True, flags=fitz.TEXT_PRESERVE_LIGATURES) for page in doc])

    extracted_text = []
    lines = text.split("\n")

    for line in lines:
        if "electricity for better life" in line.lower().strip():
            break
        extracted_text.append(line)


    extracted_text_str = "\n".join(extracted_text)
    cleaned_text = extracted_text_str.replace("\n:", "").strip()
    lines = cleaned_text.split("\n")

    keywords = [
        "Rekening", "No", "ID Pelanggan", "Nama Pelanggan", "Alamat Pelanggan", "Nama Sesuai NPWP", "Alamat Sesuai NPWP",
        "Status", "Golongan Tarif", "Faktor Kali Meter", "NIK", "Subsidi***", "kWh LWBP", "kWh WBP", "kVArh", "Tarif LWBP",
        "Tarif WBP", "Tarif kVArh", "Jatuh Tempo", "Tunggakan Bulan Sebelumnya", "BP (Biaya Penyambungan)",
        "UJL (Uang Jaminan Langganan)", "Angsuran Lainnya", "Biaya Beban / EMIN", "Total Tagihan**", "Rupiah TTL Terpakai",
        "Rupiah Kompensasi****", "Rupiah TTL minus Kompensasi","DPP Nilai Lain", "PPN*****", "PBJT-TL******",
        "dan Keandalan, sewa trafo, paralel, dll Inc. Tax", "Renewable Energy Certificate", "PPN Renewable Energy Certificate)"
    ]

    extracted_data = {key: "Tidak ditemukan" for key in keywords}
    ignored_keywords = ["Informasi Pengaduan", "Call Center 123", "Email pln123@pln.co.id", "Twitter @pln123"]

    import re

    for line in lines:
        # Abaikan baris jika ada keyword yang harus di-ignore
        if any(ignore in line for ignore in ignored_keywords):
            continue

        # Bersihkan tanda kurung dari line, tapi tetap simpan aslinya untuk nanti
        clean_line = re.sub(r'\s*\(.*?\)', '', line)

        # Tangani variasi nama PBJT-TL (semua dianggap sebagai "PBJT-TL******")
        if extracted_data["PBJT-TL******"] == "Tidak ditemukan":
            if re.search(r"PBJT[-/ ]*TL", clean_line):
                value_match = re.search(r'Rp\s*[\d.]+(?:,\d+)?', line)
                if value_match:
                    extracted_data["PBJT-TL******"] = value_match.group().strip()
                    continue  # skip ke baris berikutnya

        # Tangani keyword lain seperti biasa
        for keyword in keywords:
            if keyword in line and extracted_data[keyword] == "Tidak ditemukan":
                parts = line.split(keyword, 1)
                if len(parts) > 1:
                    value = parts[1].strip().lstrip(":")

                    if keyword in ["PPN*****", "PBJT-TL******", "DPP Nilai Lain"]:
                        # Bersihkan kurung jika ada (jika belum dibersihkan)
                        value = re.sub(r'^\(.*?\)\s*', '', value).strip()
                    else:
                        value = re.split(r'\s{3,}', value)[0].strip()

                    # Penanganan khusus untuk keyword tertentu
                    if keyword == "Rekening":
                        value = value[:7]
                    if keyword == "Jatuh Tempo" and "NPWP" in value:
                        value = re.sub(r'NPWP.*$', '', value).strip()
                    value = value.strip()

                    # Deteksi jika ada dua keyword dalam satu baris
                    for other_keyword in keywords:
                        if other_keyword in value and other_keyword != keyword:
                            value_parts = value.split(other_keyword, 1)
                            extracted_data[keyword] = value_parts[0].strip().lstrip(":")
                            extracted_data[other_keyword] = value_parts[1].strip().lstrip(":")
                            break
                    else:
                        extracted_data[keyword] = value

        df = pd.DataFrame([extracted_data])

    def format_currency(value, column_name=None):
        # Hindari pengolahan untuk kolom-kolom tertentu
        if column_name in ["NIK", "ID Pelanggan", "Rekening", "No","Golongan Tarif"]:
            return value

        if isinstance(value, str):
            if "/" in value:
                return value
            elif value.strip() in ["Tidak ditemukan", "Rp"]:
                return 0.0
            # Bersihkan string dari simbol Rp dan tanda koma
            cleaned = value.replace("Rp", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return value  # Kembalikan nilai asli jika gagal parsing

        # Jika bukan string, coba langsung konversi ke float
        try:
            return float(value)
        except (ValueError, TypeError):
            return value

    for column in df.columns:
        df[column] = df[column].apply(lambda x: format_currency(x, column))

    new_columns = [
        "Nama File", "THBL", "No Rekening", "ID Pelanggan", "Nama Pelanggan", "Alamat Pelanggan", "Nama Sesuai NPWP",
        "Alamat Sesuai NPWP", "Status", "Golongan Tarif", "Faktor Kali Meter", "NIK", "Subsidi",
        "kWh LWBP", "kWh WBP", "kVArh", "Tarif LWBP", "Tarif WBP", "Tarif kVArh", "Jatuh Tempo",
        "Tunggakan Bulan Sebelumnya", "BP (Biaya Penyambungan)", "UJL (Uang Jaminan Langganan)","Angsuran Lainnya",
        "Biaya Beban / EMIN", "Total Tagihan", "Rupiah TTL Terpakai", "Rupiah Kompensasi",
        "Rupiah TTL minus Kompensasi","DPP", "PPN", "PBJT-TL", "Rupiah Jasa Layanan dan Keandalan, sewa trafo, paralel, dll Inc. Tax",
        "Renewable Energy Certificate", "PPN Renewable Energy Certificate"
    ]

    values = [os.path.basename(file_path)] + ["Tidak ditemukan"] * (len(new_columns) - 1)
    for i, column in enumerate(df.columns):
        values[i + 1] = df.iloc[0, i]
    df = pd.DataFrame([values], columns=new_columns)
    df.at[0, "THBL"] = clean_thbl(df.at[0, "THBL"])
    df["Jatuh Tempo"] = pd.to_datetime(df["Jatuh Tempo"].apply(clean_jatuh_tempo), errors='coerce')
    df[["Angsuran Lainnya", "DPP"]] = df[["Angsuran Lainnya", "DPP"]].replace("Tidak ditemukan", 0.0).astype(float)



    return df
