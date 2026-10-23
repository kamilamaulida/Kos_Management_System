import os
from datetime import date, datetime
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()
from psycopg.errors import UniqueViolation, ForeignKeyViolation, CheckViolation, NotNullViolation

app = Flask(__name__)

# Semua nama tabel/kolom di bawah adalah allowlist; input pengguna tidak dipakai
# sebagai nama SQL secara langsung.
RESOURCES = {
    "kamar": {
        "table": "kamar", "pk": "id_kamar",
        "fields": {"nomor_kamar", "tipe", "harga_sewa", "status"},
        "required": {"nomor_kamar", "tipe", "harga_sewa"},
    },
    "penghuni": {
        "table": "penghuni", "pk": "id_penghuni",
        "fields": {"nama", "no_telepon", "email", "alamat_asal", "status"},
        "required": {"nama", "no_telepon"},
    },
    "fasilitas": {
        "table": "fasilitas", "pk": "id_fasilitas",
        "fields": {"nama_fasilitas"}, "required": {"nama_fasilitas"},
    },
    "sewa": {
        "table": "sewa", "pk": "id_sewa",
        "fields": {"id_penghuni", "id_kamar", "tanggal_masuk", "tanggal_keluar", "status"},
        "required": {"id_penghuni", "id_kamar"},
    },
    "pembayaran": {
        "table": "pembayaran", "pk": "id_pembayaran",
        "fields": {"id_sewa", "periode", "jumlah", "tanggal_bayar", "metode", "status"},
        "required": {"id_sewa", "periode", "jumlah"},
    },
    "keluhan": {
        "table": "keluhan", "pk": "id_keluhan",
        "fields": {"id_penghuni", "id_kamar", "judul", "deskripsi", "tanggal_lapor", "status"},
        "required": {"id_penghuni", "id_kamar", "judul"},
    },
}

def db_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Environment variable DATABASE_URL belum diatur.")
    # Neon dan beberapa provider memakai sslmode=require pada koneksi TLS.
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)

def json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value

def fail(message, status):
    return jsonify({"error": message}), status

def body_json():
    if not request.is_json:
        return None, fail("Header Content-Type harus application/json", 400)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, fail("Body harus berupa objek JSON", 400)
    return data, None

def clean_data(resource, data, partial=False):
    allowed = RESOURCES[resource]["fields"]
    unknown = set(data) - allowed
    if unknown:
        return None, f"Field tidak dikenal: {', '.join(sorted(unknown))}"
    if not partial:
        missing = RESOURCES[resource]["required"] - set(data)
        if missing:
            return None, f"Field wajib diisi: {', '.join(sorted(missing))}"
    return data, None

@app.get("/")
def home():
    return jsonify({
        "project": "Kos Management System API",
        "message": "REST API aktif",
        "health": "/health",
        "resources": [f"/api/{name}" for name in RESOURCES],
        "docs": "Lihat README.md pada repository"
    }), 200

@app.get("/health")
def health():
    try:
        with db_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception:
        app.logger.exception("Health check database gagal")
        return fail("API berjalan, tetapi koneksi database gagal. Periksa DATABASE_URL.", 503)

@app.errorhandler(404)
def not_found(_error):
    return fail("Endpoint tidak ditemukan", 404)

@app.errorhandler(405)
def method_not_allowed(_error):
    return fail("HTTP method tidak diizinkan untuk endpoint ini", 405)

@app.errorhandler(Exception)
def unhandled_error(error):
    # Jangan bocorkan connection string atau detail internal ke client.
    app.logger.exception("Kesalahan server: %s", error)
    return fail("Terjadi kesalahan server. Periksa log aplikasi.", 500)

def db_error_response(error):
    if isinstance(error, UniqueViolation):
        return fail("Data duplikat: periksa kolom yang harus unik atau periode pembayaran.", 409)
    if isinstance(error, ForeignKeyViolation):
        return fail("Relasi tidak valid: pastikan data referensi tersedia.", 400)
    if isinstance(error, CheckViolation):
        return fail("Nilai tidak sesuai aturan database.", 400)
    if isinstance(error, NotNullViolation):
        return fail("Ada field wajib yang belum diisi.", 400)
    app.logger.exception("Kesalahan database")
    return fail("Terjadi kesalahan saat mengakses database.", 500)

def resource_list(resource):
    config = RESOURCES[resource]
    try:
        with db_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {config['table']} ORDER BY {config['pk']}"
            ).fetchall()
        return jsonify({"data": json_safe(rows), "count": len(rows)}), 200
    except Exception as e:
        return db_error_response(e)

def resource_detail(resource, record_id):
    config = RESOURCES[resource]
    try:
        with db_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {config['table']} WHERE {config['pk']} = %s",
                (record_id,)
            ).fetchone()
        if row is None:
            return fail(f"{resource} dengan ID {record_id} tidak ditemukan", 404)
        return jsonify({"data": json_safe(row)}), 200
    except Exception as e:
        return db_error_response(e)

def resource_create(resource):
    data, error_response = body_json()
    if error_response:
        return error_response
    data, validation_error = clean_data(resource, data)
    if validation_error:
        return fail(validation_error, 400)
    config = RESOURCES[resource]
    columns = list(data.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    col_sql = ", ".join(columns)
    values = [data[col] for col in columns]
    try:
        with db_connection() as conn:
            row = conn.execute(
                f"INSERT INTO {config['table']} ({col_sql}) VALUES ({placeholders}) "
                f"RETURNING *",
                values
            ).fetchone()
        return jsonify({"message": f"{resource} berhasil ditambahkan", "data": json_safe(row)}), 201
    except Exception as e:
        return db_error_response(e)

def resource_update(resource, record_id, partial=False):
    data, error_response = body_json()
    if error_response:
        return error_response
    data, validation_error = clean_data(resource, data, partial=partial)
    if validation_error:
        return fail(validation_error, 400)
    if not data:
        return fail("Minimal satu field harus dikirim untuk diperbarui", 400)
    config = RESOURCES[resource]
    assignments = ", ".join(f"{col} = %s" for col in data)
    values = list(data.values()) + [record_id]
    try:
        with db_connection() as conn:
            row = conn.execute(
                f"UPDATE {config['table']} SET {assignments} "
                f"WHERE {config['pk']} = %s RETURNING *",
                values
            ).fetchone()
        if row is None:
            return fail(f"{resource} dengan ID {record_id} tidak ditemukan", 404)
        return jsonify({"message": f"{resource} berhasil diperbarui", "data": json_safe(row)}), 200
    except Exception as e:
        return db_error_response(e)

def resource_delete(resource, record_id):
    config = RESOURCES[resource]
    try:
        with db_connection() as conn:
            row = conn.execute(
                f"DELETE FROM {config['table']} WHERE {config['pk']} = %s RETURNING *",
                (record_id,)
            ).fetchone()
        if row is None:
            return fail(f"{resource} dengan ID {record_id} tidak ditemukan", 404)
        return jsonify({"message": f"{resource} berhasil dihapus", "data": json_safe(row)}), 200
    except Exception as e:
        return db_error_response(e)

def register_resource_routes(resource):
    # Endpoint function dibuat dengan closure agar setiap resource memakai konfigurasi tepat.
    def list_items():
        return resource_list(resource)
    def create_item():
        return resource_create(resource)
    def detail_item(record_id):
        return resource_detail(resource, record_id)
    def replace_item(record_id):
        return resource_update(resource, record_id, partial=False)
    def patch_item(record_id):
        return resource_update(resource, record_id, partial=True)
    def delete_item(record_id):
        return resource_delete(resource, record_id)

    endpoint = resource
    app.add_url_rule(f"/api/{resource}", endpoint + "_list", list_items, methods=["GET"])
    app.add_url_rule(f"/api/{resource}", endpoint + "_create", create_item, methods=["POST"])
    app.add_url_rule(f"/api/{resource}/<int:record_id>", endpoint + "_detail", detail_item, methods=["GET"])
    app.add_url_rule(f"/api/{resource}/<int:record_id>", endpoint + "_replace", replace_item, methods=["PUT"])
    app.add_url_rule(f"/api/{resource}/<int:record_id>", endpoint + "_patch", patch_item, methods=["PATCH"])
    app.add_url_rule(f"/api/{resource}/<int:record_id>", endpoint + "_delete", delete_item, methods=["DELETE"])

for resource_name in RESOURCES:
    register_resource_routes(resource_name)

# Tabel pivot many-to-many menggunakan primary key gabungan.
@app.get("/api/kamar-fasilitas")
def list_kamar_fasilitas():
    try:
        with db_connection() as conn:
            rows = conn.execute(
                """SELECT kf.id_kamar, k.nomor_kamar, kf.id_fasilitas, f.nama_fasilitas
                   FROM kamar_fasilitas kf
                   JOIN kamar k ON k.id_kamar = kf.id_kamar
                   JOIN fasilitas f ON f.id_fasilitas = kf.id_fasilitas
                   ORDER BY kf.id_kamar, kf.id_fasilitas"""
            ).fetchall()
        return jsonify({"data": json_safe(rows), "count": len(rows)}), 200
    except Exception as e:
        return db_error_response(e)

@app.post("/api/kamar-fasilitas")
def create_kamar_fasilitas():
    data, error_response = body_json()
    if error_response:
        return error_response
    if not {"id_kamar", "id_fasilitas"}.issubset(data) or set(data) - {"id_kamar", "id_fasilitas"}:
        return fail("Body wajib berisi id_kamar dan id_fasilitas saja", 400)
    try:
        with db_connection() as conn:
            row = conn.execute(
                """INSERT INTO kamar_fasilitas (id_kamar, id_fasilitas)
                   VALUES (%s, %s) RETURNING id_kamar, id_fasilitas""",
                (data["id_kamar"], data["id_fasilitas"])
            ).fetchone()
        return jsonify({"message": "Fasilitas berhasil ditambahkan ke kamar", "data": row}), 201
    except Exception as e:
        return db_error_response(e)

@app.delete("/api/kamar-fasilitas/<int:id_kamar>/<int:id_fasilitas>")
def delete_kamar_fasilitas(id_kamar, id_fasilitas):
    try:
        with db_connection() as conn:
            row = conn.execute(
                """DELETE FROM kamar_fasilitas
                   WHERE id_kamar = %s AND id_fasilitas = %s
                   RETURNING id_kamar, id_fasilitas""",
                (id_kamar, id_fasilitas)
            ).fetchone()
        if row is None:
            return fail("Relasi kamar dan fasilitas tidak ditemukan", 404)
        return jsonify({"message": "Relasi kamar-fasilitas berhasil dihapus", "data": row}), 200
    except Exception as e:
        return db_error_response(e)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", "5000")))
