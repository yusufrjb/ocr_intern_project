import psycopg2
from psycopg2.extras import execute_values
import os

DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgre',
    'user': 'postgres',
    'password': '0407084sd'
}

def connect_db():
    return psycopg2.connect(**DB_PARAMS)

def insert_data_if_not_exists(df):
    conn = connect_db()
    cur = conn.cursor()

    # Cek duplikat berdasarkan (thbl, id_pelanggan)
    thbl = df.at[0, "THBL"]
    id_pel = df.at[0, "ID Pelanggan"]
    cur.execute("SELECT COUNT(*) FROM tagihan_pln WHERE thbl=%s AND id_pelanggan=%s", (thbl, id_pel))
    exists = cur.fetchone()[0] > 0

    if exists or thbl == "Tidak ditemukan" or id_pel == "Tidak ditemukan":
        print("❌ Duplikat atau data tidak lengkap, tidak disimpan.")
        return False

    # Susun urutan data sesuai tabel
    columns = [col.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("*", "").replace("-", "_") for col in df.columns]
    values = tuple(df.iloc[0])

    placeholders = ', '.join(['%s'] * len(values))
    column_names = ', '.join(columns)

    query = f"INSERT INTO tagihan_pln ({column_names}) VALUES ({placeholders})"
    cur.execute(query, values)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Data berhasil disimpan ke database.")
    return True
