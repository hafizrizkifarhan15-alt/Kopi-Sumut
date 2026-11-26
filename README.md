# ☕ KOPI_SUMUT

**Sistem Informasi Luas Lahan dan Produksi Kopi Provinsi Sumatera Utara**

KOPI_SUMUT adalah dashboard berbasis web yang menampilkan data luas lahan dan hasil produksi kopi per kecamatan di tujuh kabupaten di Sumatera Utara. Data tiap kabupaten disimpan di database masing-masing, lalu disinkronkan otomatis ke database pusat dan ditampilkan melalui dashboard Streamlit.

---

## Fitur

- **Dashboard Utama**: ringkasan total kabupaten, kecamatan, luas lahan, dan produksi, serta 10 kecamatan dengan produksi tertinggi.
- **Statistik Kabupaten**: perbandingan luas lahan, produksi, dan produktivitas (ton/ha) antar kabupaten.
- **Statistik Kecamatan**: peringkat produksi per kecamatan dan hubungan luas lahan dengan hasil produksi.
- **Data Kecamatan**: tabel lengkap dengan pencarian dan filter kabupaten.
- **Peta Persebaran Kopi**: peta produksi kopi per kabupaten.
- **Sinkronisasi otomatis** dari database daerah ke database pusat melalui GitHub Actions.

---

## Cakupan Wilayah

| Kode | Kabupaten | Jumlah Kecamatan |
|---|---|---|
| KAR | Karo | 17 |
| DAI | Dairi | 15 |
| HUM | Humbang Hasundutan | 10 |
| TAPUT | Tapanuli Utara | 15 |
| TAPSEL | Tapanuli Selatan | 15 |
| SIM | Simalungun | 32 |
| MAN | Mandailing Natal | 23 |
| | **Total** | **127** |

---

## Arsitektur

```
┌────────────────────┐
│ Database Daerah    │  (7 database PostgreSQL di Neon)
│ tabel: produksi    │
└─────────┬──────────┘
          │  sync.py (GitHub Actions)
          ▼
┌────────────────────┐
│ Database Pusat     │
│ tabel:             │
│ produksi_pusat     │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Dashboard Streamlit│
│ app.py             │
└────────────────────┘
```

---

## Struktur Database

### Tabel `produksi` (di setiap database daerah)

```sql
CREATE TABLE produksi (
    kode_daerah    VARCHAR(20) PRIMARY KEY,
    nama_kecamatan VARCHAR(100) NOT NULL,
    kabupaten      VARCHAR(100),
    luas_lahan     DECIMAL(10,2),
    hasil_produksi DECIMAL(10,2),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabel `produksi_pusat` (di database pusat)

```sql
CREATE TABLE produksi_pusat (
    kode_daerah    VARCHAR(20) PRIMARY KEY,
    nama_kecamatan VARCHAR(100) NOT NULL,
    kabupaten      VARCHAR(100),
    luas_lahan     DECIMAL(10,2),
    hasil_produksi DECIMAL(10,2),
    wilayah_sumber VARCHAR(50),
    updated_at     TIMESTAMPTZ
);
```

Satuan: `luas_lahan` dalam hektar (ha) dan `hasil_produksi` dalam ton.

---

## Sumber Data

Data bersumber dari publikasi Badan Pusat Statistik (BPS) tiap kabupaten, subjek perkebunan. Karena tiap kabupaten menerbitkan data dengan format dan tahun yang berbeda, perhatikan catatan berikut:

| Kabupaten | Data yang dipakai |
|---|---|
| Karo | Kopi, 2025 |
| Dairi | Kopi Arabika, 2025 |
| Humbang Hasundutan | Kopi, 2025 |
| Tapanuli Utara | Kopi, **2024** (kolom 2025 belum tersedia) |
| Tapanuli Selatan | Kopi Arabika (tabel tanpa kolom tahun) |
| Simalungun | Kopi, kolom Jumlah/Total luas areal |
| Mandailing Natal | Kopi, 2025 |

**Catatan kualitas data:**

- Tanda "-" pada tabel BPS ditulis sebagai `0.00`.
- Pada Tapanuli Utara, nilai `luas_lahan` dan `hasil_produksi` saat ini identik karena tabel produksi yang tersedia ternyata sama dengan tabel luas lahan. Data produksi yang benar perlu dimasukkan.
- Angka produktivitas (ton/ha) bisa tidak mewakili kondisi sebenarnya bila luas lahan mencakup tanaman belum menghasilkan.

---

## Teknologi

- **Python 3.11**
- **Streamlit**: antarmuka dashboard
- **Plotly**: grafik interaktif
- **Pandas**: pengolahan data
- **psycopg2**: koneksi PostgreSQL
- **Neon**: database PostgreSQL
- **GitHub Actions**: sinkronisasi terjadwal

---

## Struktur Proyek

```
.
├── .github/
│   └── workflows/
│       └── sync.yml        # Workflow sinkronisasi database
├── app.py                  # Dashboard Streamlit
├── sync.py                 # Skrip sinkronisasi daerah ke pusat
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Instalasi Lokal

1. **Clone repositori**

   ```bash
   git clone https://github.com/<username>/<nama-repositori>.git
   cd <nama-repositori>
   ```

2. **Buat virtual environment dan pasang dependensi**

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Atur koneksi database pusat**

   Buat file `.streamlit/secrets.toml`:

   ```toml
   [datawarehouse]
   url = "postgresql://user:password@host/dbname?sslmode=require"
   ```

   Atau gunakan environment variable:

   ```bash
   export DATAWAREHOUSE_URL="postgresql://user:password@host/dbname?sslmode=require"
   ```

4. **Jalankan dashboard**

   ```bash
   streamlit run app.py
   ```

---

## Sinkronisasi Otomatis (GitHub Actions)

Workflow `sync.yml` menjalankan `sync.py` secara terjadwal untuk menarik data dari tujuh database daerah dan memasukkannya ke `produksi_pusat`. Workflow juga bisa dijalankan manual lewat tab **Actions** → **Run workflow**.

Tambahkan secret berikut di **Settings → Secrets and variables → Actions**:

| Secret | Keterangan |
|---|---|
| `DB_KARO` | Connection string database Karo |
| `DB_DAIRI` | Connection string database Dairi |
| `DB_HUMBANG_HASUNDUTAN` | Connection string database Humbang Hasundutan |
| `DB_TAPANULI_UTARA` | Connection string database Tapanuli Utara |
| `DB_TAPANULI_SELATAN` | Connection string database Tapanuli Selatan |
| `DB_SIMALUNGUN` | Connection string database Simalungun |
| `DB_MANDAILING_NATAL` | Connection string database Mandailing Natal |
| `DB_PUSAT` | Connection string database pusat |

Logika sinkronisasi memakai `INSERT ... ON CONFLICT (kode_daerah) DO UPDATE`, sehingga data lama diperbarui hanya jika `updated_at` dari daerah lebih baru atau sama dengan yang ada di pusat.

---

## Deploy ke Streamlit Cloud

1. Hubungkan repositori ini ke [Streamlit Community Cloud](https://streamlit.io/cloud).
2. Pilih `app.py` sebagai file utama.
3. Pada **Settings → Secrets**, tambahkan:

   ```toml
   [datawarehouse]
   url = "postgresql://user:password@host/dbname?sslmode=require"
   ```

   Isi `url` dengan connection string **database pusat**.

---

## Keamanan

- Jangan pernah meng-commit `.streamlit/secrets.toml` atau `.env`. Keduanya sudah masuk `.gitignore`.
- Simpan semua connection string di GitHub Secrets dan Streamlit Secrets.
- Jika kredensial sempat ter-commit, segera ganti password database di Neon.

---

## Lisensi

Tentukan lisensi proyek ini (misalnya MIT) dan tambahkan file `LICENSE`.

---

## Sumber Data & Kredit

Data produksi dan luas lahan kopi: Badan Pusat Statistik (BPS) Kabupaten Karo, Dairi, Humbang Hasundutan, Tapanuli Utara, Tapanuli Selatan, Simalungun, dan Mandailing Natal.
