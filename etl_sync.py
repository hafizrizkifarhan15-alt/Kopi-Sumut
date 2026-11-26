import os
import psycopg2


def sync_karo():
    source_url = os.getenv("DB_KARO")
    target_url = os.getenv("DB_PUSAT")

    if not source_url or not target_url:
        raise RuntimeError(
            "Secret DB_KARO atau DB_PUSAT belum tersedia."
        )

    source_conn = None
    target_conn = None

    try:
        # Koneksi database sumber: DB Karo
        source_conn = psycopg2.connect(
            source_url,
            sslmode="require",
            connect_timeout=20
        )

        with source_conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    kode_daerah,
                    nama_kecamatan,
                    kabupaten,
                    luas_lahan,
                    hasil_produksi,
                    updated_at
                FROM public.produksi
            """)
            data = cursor.fetchall()

        print(f"Data ditemukan dari DB Karo: {len(data)} baris")

        if not data:
            print("Tidak ada data untuk disinkronkan.")
            return

        # Koneksi database tujuan: Data Warehouse pusat
        target_conn = psycopg2.connect(
            target_url,
            sslmode="require",
            connect_timeout=20
        )

        with target_conn.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO public.produksi_pusat (
                    kode_daerah,
                    nama_kecamatan,
                    kabupaten,
                    luas_lahan,
                    hasil_produksi,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)

                ON CONFLICT (kode_daerah, kabupaten)
                DO UPDATE SET
                    nama_kecamatan = EXCLUDED.nama_kecamatan,
                    luas_lahan = EXCLUDED.luas_lahan,
                    hasil_produksi = EXCLUDED.hasil_produksi,
                    updated_at = EXCLUDED.updated_at
            """, data)

        target_conn.commit()

        print(f"Berhasil menyinkronkan {len(data)} baris DB Karo.")

    except Exception:
        if target_conn is not None:
            target_conn.rollback()
        raise

    finally:
        if source_conn is not None:
            source_conn.close()

        if target_conn is not None:
            target_conn.close()


if __name__ == "__main__":
    sync_karo()
