-- =====================================================
-- Struktur Database: Kos Management System
-- DBMS : PostgreSQL
--
-- Relasi:
--   1:N  penghuni  -> sewa
--   1:N  kamar     -> sewa
--   1:N  sewa      -> pembayaran
--   1:N  penghuni  -> keluhan
--   1:N  kamar     -> keluhan
--   N:N  kamar <-> fasilitas (lewat kamar_fasilitas)
--
-- Pemetaan fungsi ke tabel:
--   getDataKamar, cekKetersediaanKamar, ubahStatusKamar -> kamar
--   getDataPenghuni, tambahPenghuni                     -> penghuni
--   pindahKamar, keluarKos                              -> sewa
--   catatPembayaran, cekStatusPembayaran,
--   getRiwayatPembayaran                                -> pembayaran
--   buatLaporanKeluhan, updateStatusKeluhan             -> keluhan
-- =====================================================

DROP TABLE IF EXISTS kamar_fasilitas CASCADE;
DROP TABLE IF EXISTS keluhan CASCADE;
DROP TABLE IF EXISTS pembayaran CASCADE;
DROP TABLE IF EXISTS sewa CASCADE;
DROP TABLE IF EXISTS fasilitas CASCADE;
DROP TABLE IF EXISTS penghuni CASCADE;
DROP TABLE IF EXISTS kamar CASCADE;

-- 1. Tabel kamar
CREATE TABLE kamar (
    id_kamar    SERIAL PRIMARY KEY,
    nomor_kamar VARCHAR(10)   NOT NULL UNIQUE,
    tipe        VARCHAR(30)   NOT NULL,
    harga_sewa  NUMERIC(12,2) NOT NULL CHECK (harga_sewa >= 0),
    status      VARCHAR(20)   NOT NULL DEFAULT 'tersedia'
        CHECK (status IN ('tersedia', 'dihuni', 'perbaikan'))
);

-- 2. Tabel penghuni
CREATE TABLE penghuni (
    id_penghuni SERIAL PRIMARY KEY,
    nama        VARCHAR(100) NOT NULL,
    no_telepon  VARCHAR(15)  NOT NULL,
    email       VARCHAR(100) UNIQUE,
    alamat_asal TEXT,
    status      VARCHAR(20)  NOT NULL DEFAULT 'aktif'
        CHECK (status IN ('aktif', 'keluar'))
);

-- 3. Tabel fasilitas
CREATE TABLE fasilitas (
    id_fasilitas   SERIAL PRIMARY KEY,
    nama_fasilitas VARCHAR(50) NOT NULL UNIQUE
);

-- 4. Tabel kamar_fasilitas (relasi N:N antara kamar dan fasilitas)
CREATE TABLE kamar_fasilitas (
    id_kamar     INT NOT NULL,
    id_fasilitas INT NOT NULL,
    PRIMARY KEY (id_kamar, id_fasilitas),
    CONSTRAINT fk_kf_kamar
        FOREIGN KEY (id_kamar) REFERENCES kamar (id_kamar)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_kf_fasilitas
        FOREIGN KEY (id_fasilitas) REFERENCES fasilitas (id_fasilitas)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- 5. Tabel sewa (riwayat kamar yang ditempati penghuni)
--    Pindah kamar = sewa lama diubah 'pindah', lalu dibuat sewa baru.
--    Keluar kos   = sewa diubah 'selesai' dan tanggal_keluar diisi.
CREATE TABLE sewa (
    id_sewa        SERIAL PRIMARY KEY,
    id_penghuni    INT  NOT NULL,
    id_kamar       INT  NOT NULL,
    tanggal_masuk  DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_keluar DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'aktif'
        CHECK (status IN ('aktif', 'pindah', 'selesai')),
    CONSTRAINT fk_sewa_penghuni
        FOREIGN KEY (id_penghuni) REFERENCES penghuni (id_penghuni)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_sewa_kamar
        FOREIGN KEY (id_kamar) REFERENCES kamar (id_kamar)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_sewa_tanggal
        CHECK (tanggal_keluar IS NULL OR tanggal_keluar >= tanggal_masuk)
);

-- Satu kamar hanya boleh punya satu sewa aktif,
-- dan satu penghuni hanya boleh punya satu sewa aktif.
CREATE UNIQUE INDEX uq_sewa_kamar_aktif
    ON sewa (id_kamar) WHERE status = 'aktif';
CREATE UNIQUE INDEX uq_sewa_penghuni_aktif
    ON sewa (id_penghuni) WHERE status = 'aktif';

-- 6. Tabel pembayaran
CREATE TABLE pembayaran (
    id_pembayaran SERIAL PRIMARY KEY,
    id_sewa       INT  NOT NULL,
    periode       DATE NOT NULL,  -- isi tanggal 1 dari bulan yang dibayar
    jumlah        NUMERIC(12,2) NOT NULL CHECK (jumlah > 0),
    tanggal_bayar DATE,
    metode        VARCHAR(20)
        CHECK (metode IN ('tunai', 'transfer', 'e-wallet')),
    status        VARCHAR(20) NOT NULL DEFAULT 'belum_bayar'
        CHECK (status IN ('belum_bayar', 'lunas')),
    CONSTRAINT fk_bayar_sewa
        FOREIGN KEY (id_sewa) REFERENCES sewa (id_sewa)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_bayar_periode UNIQUE (id_sewa, periode)
);

-- 7. Tabel keluhan
CREATE TABLE keluhan (
    id_keluhan    SERIAL PRIMARY KEY,
    id_penghuni   INT          NOT NULL,
    id_kamar      INT          NOT NULL,
    judul         VARCHAR(150) NOT NULL,
    deskripsi     TEXT,
    tanggal_lapor DATE         NOT NULL DEFAULT CURRENT_DATE,
    status        VARCHAR(20)  NOT NULL DEFAULT 'diajukan'
        CHECK (status IN ('diajukan', 'diproses', 'selesai')),
    CONSTRAINT fk_keluhan_penghuni
        FOREIGN KEY (id_penghuni) REFERENCES penghuni (id_penghuni)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_keluhan_kamar
        FOREIGN KEY (id_kamar) REFERENCES kamar (id_kamar)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Index untuk mempercepat pencarian
CREATE INDEX idx_sewa_penghuni     ON sewa (id_penghuni);
CREATE INDEX idx_sewa_kamar        ON sewa (id_kamar);
CREATE INDEX idx_pembayaran_sewa   ON pembayaran (id_sewa);
CREATE INDEX idx_keluhan_penghuni  ON keluhan (id_penghuni);
CREATE INDEX idx_keluhan_kamar     ON keluhan (id_kamar);

-- =====================================================
-- Contoh data (opsional, untuk uji coba)
-- =====================================================
INSERT INTO kamar (nomor_kamar, tipe, harga_sewa, status) VALUES
    ('A01', 'Standar', 800000, 'dihuni'),
    ('A02', 'Standar', 800000, 'tersedia'),
    ('B01', 'VIP',    1200000, 'perbaikan');

INSERT INTO fasilitas (nama_fasilitas) VALUES
    ('Kasur'), ('Lemari'), ('AC'), ('Kamar Mandi Dalam');

INSERT INTO kamar_fasilitas (id_kamar, id_fasilitas) VALUES
    (1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3), (3, 4);

INSERT INTO penghuni (nama, no_telepon, email, alamat_asal) VALUES
    ('Budi Santoso', '081234567890', 'budi@example.com', 'Kebumen');

INSERT INTO sewa (id_penghuni, id_kamar, tanggal_masuk) VALUES
    (1, 1, '2026-09-01');

INSERT INTO pembayaran (id_sewa, periode, jumlah, tanggal_bayar, metode, status) VALUES
    (1, '2026-09-01', 800000, '2026-09-02', 'transfer', 'lunas'),
    (1, '2026-10-01', 800000, NULL, NULL, 'belum_bayar');

INSERT INTO keluhan (id_penghuni, id_kamar, judul, deskripsi) VALUES
    (1, 1, 'Lampu kamar mati', 'Lampu utama tidak menyala sejak kemarin.');
