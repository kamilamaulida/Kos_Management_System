# Checklist pengumpulan — Kos Management System

## Berkas yang disiapkan dalam paket
- Source code Flask: `app.py`
- SQL database: `database.sql`
- Rancangan ERD: `schema.dbml`
- Dokumentasi API: `README.md`
- Template request Postman: `tests/Kos_Management_System.postman_collection.json`
- Contoh environment: `.env.example`

## Harus diverifikasi sebelum dikumpulkan
- [ ] Jalankan SQL di database PostgreSQL online baru.
- [ ] Atur `DATABASE_URL` lokal dan di Vercel; jangan bagikan nilai rahasianya.
- [ ] Jalankan API lokal dan periksa `/health`.
- [ ] Tes GET, POST, PUT, PATCH, DELETE dan simpan hasil aktual.
- [ ] Buat repository GitHub dan unggah semua berkas kecuali `.env` dan `.venv`.
- [ ] Deploy repository ke Vercel.
- [ ] Ganti `baseUrl` di koleksi Postman ke URL Vercel dan jalankan ulang request.
- [ ] Ekspor ERD sebagai gambar dan masukkan ke dokumentasi.
- [ ] Sertakan URL GitHub, URL Vercel, dokumentasi, dan screenshot/export pengujian aktual.

**Penting:** koleksi Postman ini adalah template request, bukan bukti bahwa API telah berhasil diuji. SQL memuat `DROP TABLE`, jadi hanya jalankan pada database baru atau database yang datanya memang boleh dihapus.
