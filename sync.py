import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st


# ==========================================
# 1. KONFIGURASI WEBSITE
# ==========================================

st.set_page_config(
    page_title="KOPI_SUMUT",
    page_icon="☕",
    layout="wide"
)

st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}

[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. KONEKSI DATABASE PUSAT
# ==========================================

def get_database_url():

    # 1. Prioritaskan environment variable (GitHub Actions)
    database_url = os.getenv("DATAWAREHOUSE_URL")

    if database_url:
        return database_url

    # 2. Jika dijalankan di Streamlit Cloud, pakai Streamlit Secrets
    try:
        return st.secrets["datawarehouse"]["url"]

    except Exception as e:
        raise RuntimeError(
            "Koneksi database pusat belum dikonfigurasi. "
            "Tambahkan DATAWAREHOUSE_URL pada GitHub Actions "
            "atau [datawarehouse].url pada Streamlit Secrets."
        ) from e


def read_data(query, params=None):

    conn = None

    try:
        conn = psycopg2.connect(
            get_database_url(),
            connect_timeout=20,
            sslmode="require",
            application_name="KOPI_SUMUT"
        )

        with conn.cursor() as cur:
            cur.execute(query, params)

            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()

        df = pd.DataFrame(rows, columns=columns)

        # Pastikan kolom angka bertipe float (DECIMAL dari PostgreSQL)
        for col in df.columns:
            if col.startswith(("total_", "luas_", "hasil_", "produktivitas")):
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    except psycopg2.Error as e:
        st.error(f"Database Error: {type(e).__name__}: {e}")
        raise

    except Exception as e:
        st.error(f"Application Error: {type(e).__name__}: {e}")
        raise

    finally:
        if conn is not None:
            conn.close()


# ==========================================
# 3. HEADER
# ==========================================

st.title("☕ KOPI_SUMUT")

st.markdown("""
**Sistem Informasi Luas Lahan dan Produksi Kopi
Provinsi Sumatera Utara**

Government Agricultural Data Dashboard
""")

st.divider()


# ==========================================
# 4. CEK KETERSEDIAAN DATA
# ==========================================

cek = read_data("SELECT COUNT(*) AS jumlah FROM produksi_pusat")

if int(cek.iloc[0]["jumlah"]) == 0:
    st.warning("Belum terdapat data pada database pusat.")
    st.stop()


# ==========================================
# 5. SIDEBAR NAVIGASI
# ==========================================

menu = st.sidebar.radio(
    "MENU NAVIGASI",
    [
        "Dashboard Utama",
        "Statistik Kabupaten",
        "Statistik Kecamatan",
        "Data Kecamatan",
        "Peta Persebaran Kopi"
    ]
)

if st.sidebar.button("Muat Ulang Data"):
    st.rerun()


# ==========================================
# 6. DASHBOARD UTAMA
# ==========================================

if menu == "Dashboard Utama":

    summary = read_data("""
        SELECT
            COUNT(*) AS total_kecamatan,
            COUNT(DISTINCT kabupaten) AS total_kabupaten,
            COALESCE(SUM(luas_lahan), 0) AS total_luas,
            COALESCE(SUM(hasil_produksi), 0) AS total_produksi,
            MAX(updated_at) AS terakhir_update
        FROM produksi_pusat
    """)

    row = summary.iloc[0]

    st.subheader("Ringkasan Data Kopi")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Kabupaten", f'{int(row["total_kabupaten"]):,}')
    col2.metric("Total Kecamatan", f'{int(row["total_kecamatan"]):,}')
    col3.metric("Total Luas Lahan", f'{float(row["total_luas"]):,.2f} ha')
    col4.metric("Total Produksi", f'{float(row["total_produksi"]):,.2f} ton')

    if pd.notna(row["terakhir_update"]):
        st.caption(
            f'Data terakhir diperbarui: {row["terakhir_update"]:%d-%m-%Y %H:%M}'
        )

    df_top = read_data("""
        SELECT nama_kecamatan, kabupaten, hasil_produksi
        FROM produksi_pusat
        ORDER BY hasil_produksi DESC
        LIMIT 10
    """)

    fig = px.bar(
        df_top.sort_values("hasil_produksi", ascending=True),
        x="hasil_produksi",
        y="nama_kecamatan",
        color="kabupaten",
        orientation="h",
        title="10 Kecamatan dengan Produksi Kopi Tertinggi",
        labels={
            "hasil_produksi": "Hasil Produksi (ton)",
            "nama_kecamatan": "Kecamatan",
            "kabupaten": "Kabupaten"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# 7. STATISTIK KABUPATEN
# ==========================================

elif menu == "Statistik Kabupaten":

    df_kabupaten = read_data("""
        SELECT
            kabupaten,
            COUNT(*) AS total_kecamatan,
            COALESCE(SUM(luas_lahan), 0) AS total_luas_lahan,
            COALESCE(SUM(hasil_produksi), 0) AS total_produksi,
            ROUND(
                COALESCE(SUM(hasil_produksi), 0)
                / NULLIF(SUM(luas_lahan), 0), 2
            ) AS produktivitas
        FROM produksi_pusat
        GROUP BY kabupaten
        ORDER BY total_produksi DESC
    """)

    st.subheader("Statistik Kopi Berdasarkan Kabupaten")

    if df_kabupaten.empty:
        st.warning("Data statistik kabupaten tidak tersedia.")

    else:
        col1, col2, col3 = st.columns(3)

        col1.metric("Jumlah Kabupaten", len(df_kabupaten))
        col2.metric(
            "Total Luas Lahan",
            f'{df_kabupaten["total_luas_lahan"].sum():,.2f} ha'
        )
        col3.metric(
            "Total Produksi",
            f'{df_kabupaten["total_produksi"].sum():,.2f} ton'
        )

        fig_luas = px.bar(
            df_kabupaten.sort_values("total_luas_lahan", ascending=True),
            x="total_luas_lahan",
            y="kabupaten",
            orientation="h",
            title="Luas Lahan Kopi per Kabupaten",
            labels={
                "total_luas_lahan": "Luas Lahan (ha)",
                "kabupaten": "Kabupaten"
            }
        )
        st.plotly_chart(fig_luas, use_container_width=True)

        fig_prod = px.bar(
            df_kabupaten.sort_values("total_produksi", ascending=True),
            x="total_produksi",
            y="kabupaten",
            orientation="h",
            title="Hasil Produksi Kopi per Kabupaten",
            labels={
                "total_produksi": "Hasil Produksi (ton)",
                "kabupaten": "Kabupaten"
            }
        )
        st.plotly_chart(fig_prod, use_container_width=True)

        st.markdown("### Rekap per Kabupaten")

        st.dataframe(
            df_kabupaten.rename(columns={
                "kabupaten": "Kabupaten",
                "total_kecamatan": "Jumlah Kecamatan",
                "total_luas_lahan": "Luas Lahan (ha)",
                "total_produksi": "Produksi (ton)",
                "produktivitas": "Produktivitas (ton/ha)"
            }),
            use_container_width=True,
            hide_index=True
        )


# ==========================================
# 8. STATISTIK KECAMATAN
# ==========================================

elif menu == "Statistik Kecamatan":

    df_kec = read_data("""
        SELECT
            nama_kecamatan,
            kabupaten,
            luas_lahan,
            hasil_produksi
        FROM produksi_pusat
    """)

    st.subheader("Statistik Kopi Berdasarkan Kecamatan")

    if df_kec.empty:
        st.warning("Data statistik kecamatan tidak tersedia.")

    else:
        col1, col2 = st.columns(2)

        with col1:
            pilihan = st.selectbox(
                "Filter Kabupaten",
                ["Semua Kabupaten"] + sorted(
                    df_kec["kabupaten"].dropna().unique().tolist()
                )
            )

        with col2:
            top_n = st.slider("Jumlah kecamatan ditampilkan", 5, 30, 15)

        if pilihan != "Semua Kabupaten":
            df_kec = df_kec[df_kec["kabupaten"] == pilihan]

        df_top = df_kec.sort_values(
            "hasil_produksi", ascending=False
        ).head(top_n)

        fig = px.bar(
            df_top.sort_values("hasil_produksi", ascending=True),
            x="hasil_produksi",
            y="nama_kecamatan",
            color="kabupaten",
            orientation="h",
            title=f"{top_n} Kecamatan dengan Produksi Tertinggi",
            labels={
                "hasil_produksi": "Hasil Produksi (ton)",
                "nama_kecamatan": "Kecamatan",
                "kabupaten": "Kabupaten"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

        df_scatter = df_kec[df_kec["luas_lahan"] > 0]

        fig_scatter = px.scatter(
            df_scatter,
            x="luas_lahan",
            y="hasil_produksi",
            color="kabupaten",
            hover_name="nama_kecamatan",
            title="Hubungan Luas Lahan dan Hasil Produksi",
            labels={
                "luas_lahan": "Luas Lahan (ha)",
                "hasil_produksi": "Hasil Produksi (ton)",
                "kabupaten": "Kabupaten"
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)


# ==========================================
# 9. DATA KECAMATAN
# ==========================================

elif menu == "Data Kecamatan":

    df_data = read_data("""
    SELECT
        kode_daerah,
        nama_kecamatan,
        kabupaten,
        luas_lahan,
        hasil_produksi,
        updated_at
    FROM produksi_pusat
    ORDER BY kabupaten, kode_daerah
""")

    st.subheader("Data Kopi per Kecamatan Sumatera Utara")

    if df_data.empty:
        st.warning("Data kecamatan tidak tersedia.")

    else:
        search = st.text_input("Cari nama kecamatan atau kode daerah")

        col1, col2 = st.columns(2)

        with col1:
            kabupaten_pilih = st.selectbox(
                "Filter Kabupaten",
                ["Semua Kabupaten"] + sorted(
                    df_data["kabupaten"].dropna().astype(str).unique().tolist()
                )
            )

        with col2:
            sembunyikan_nol = st.checkbox(
                "Sembunyikan kecamatan tanpa data (0 ha)",
                value=False
            )

        df_tampil = df_data.copy()

        if search.strip():
            mask = (
                df_tampil["nama_kecamatan"].astype(str)
                .str.contains(search.strip(), case=False, na=False)
                |
                df_tampil["kode_daerah"].astype(str)
                .str.contains(search.strip(), case=False, na=False)
            )
            df_tampil = df_tampil[mask]

        if kabupaten_pilih != "Semua Kabupaten":
            df_tampil = df_tampil[df_tampil["kabupaten"] == kabupaten_pilih]

        if sembunyikan_nol:
            df_tampil = df_tampil[df_tampil["luas_lahan"] > 0]

        st.caption(
            f"Menampilkan {len(df_tampil)} dari {len(df_data)} data kecamatan."
        )

        st.dataframe(
            df_tampil.rename(columns={
                "kode_daerah": "Kode Daerah",
                "nama_kecamatan": "Kecamatan",
                "kabupaten": "Kabupaten",
                "luas_lahan": "Luas Lahan (ha)",
                "hasil_produksi": "Produksi (ton)",
                "updated_at": "Diperbarui"
            }),
            use_container_width=True,
            hide_index=True
        )


# ==========================================
# 10. PETA PERSEBARAN KOPI
# ==========================================

elif menu == "Peta Persebaran Kopi":

    st.subheader("Peta Persebaran Kopi Sumatera Utara")

    # Tabel produksi_pusat tidak menyimpan koordinat, sehingga peta memakai
    # titik pusat kabupaten (perkiraan).
    koordinat_kabupaten = {
        "Karo":               (3.10, 98.50),
        "Dairi":              (2.75, 98.25),
        "Humbang Hasundutan": (2.27, 98.50),
        "Tapanuli Utara":     (2.02, 99.05),
        "Tapanuli Selatan":   (1.55, 99.27),
        "Simalungun":         (2.95, 99.00),
        "Mandailing Natal":   (0.80, 99.45),
    }

    df_peta = read_data("""
        SELECT
            kabupaten,
            COUNT(*) AS total_kecamatan,
            COALESCE(SUM(luas_lahan), 0) AS total_luas_lahan,
            COALESCE(SUM(hasil_produksi), 0) AS total_produksi
        FROM produksi_pusat
        GROUP BY kabupaten
        ORDER BY total_produksi DESC
    """)

    df_peta["latitude"] = df_peta["kabupaten"].map(
        lambda k: koordinat_kabupaten.get(k, (None, None))[0]
    )
    df_peta["longitude"] = df_peta["kabupaten"].map(
        lambda k: koordinat_kabupaten.get(k, (None, None))[1]
    )

    tidak_terpetakan = df_peta[df_peta["latitude"].isna()]["kabupaten"].tolist()

    df_peta = df_peta.dropna(subset=["latitude", "longitude"])

    if df_peta.empty:
        st.warning("Data persebaran kopi tidak tersedia.")

    else:
        col1, col2, col3 = st.columns(3)

        col1.metric("Kabupaten Terpetakan", f"{len(df_peta):,}")
        col2.metric(
            "Total Luas Lahan",
            f'{float(df_peta["total_luas_lahan"].sum()):,.2f} ha'
        )
        col3.metric(
            "Total Produksi",
            f'{float(df_peta["total_produksi"].sum()):,.2f} ton'
        )

        # Ukuran titik (meter) mengikuti akar produksi agar tidak terlalu timpang
        df_peta["ukuran"] = (df_peta["total_produksi"] ** 0.5) * 300

        st.markdown("### Peta Produksi Kopi per Kabupaten")

        st.map(
            df_peta,
            latitude="latitude",
            longitude="longitude",
            size="ukuran",
            zoom=6
        )

        st.caption(
            "Ukuran titik menunjukkan besar produksi kopi. "
            "Lokasi titik adalah perkiraan pusat kabupaten."
        )

        if tidak_terpetakan:
            st.warning(
                "Kabupaten berikut belum punya koordinat: "
                + ", ".join(tidak_terpetakan)
            )

        st.markdown("### Rincian Persebaran")

        st.dataframe(
            df_peta[[
                "kabupaten", "total_kecamatan",
                "total_luas_lahan", "total_produksi"
            ]].rename(columns={
                "kabupaten": "Kabupaten",
                "total_kecamatan": "Jumlah Kecamatan",
                "total_luas_lahan": "Luas Lahan (ha)",
                "total_produksi": "Produksi (ton)"
            }),
            use_container_width=True,
            hide_index=True
        )
