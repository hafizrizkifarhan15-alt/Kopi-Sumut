import os
import psycopg2


def sync_source(source_env, source_name):
    source_url = os.getenv(source_env)
    target_url = os.getenv("DB_PUSAT")

    if not source_url or not target_url:
        raise RuntimeError(
            f"Secret {source_env} atau DB_PUSAT belum tersedia."
        )

    source_conn = None
    target_conn = None

    try:
        # Koneksi database sumber
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

        print(f"{source_name}: {len(data)} data ditemukan.")

        if not data:
            print(f"{source_name}: Tidak ada data untuk disinkronkan.")
            return

        # Koneksi database pusat
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

        print(
            f"{source_name}: Berhasil menyinkronkan "
            f"{len(data)} data ke database pusat."
        )

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

    print("MEMULAI SINKRONISASI KOPI SUMATERA UTARA")

    # Kabupaten Karo
    sync_source("DB_KARO", "DB Karo")

    # Kabupaten Dairi
    sync_source("DB_DAIRI", "DB Dairi")

    # Kabupaten Humbang Hasundutan
    sync_source(
        "DB_HUMBANG_HASUNDUTAN",
        "Humbang Hasundutan"
    )

    # Kabupaten Tapanuli Utara
    sync_source(
        "DB_TAPANULI_UTARA",
        "Tapanuli Utara"
    )

    # Kabupaten Tapanuli Selatan
    sync_source(
        "DB_TAPANULI_SELATAN",
        "Tapanuli Selatan"
    )

    # Kabupaten Simalungun
    sync_source(
        "DB_SIMALUNGUN",
        "Simalungun"
    )

    print("SINKRONISASI SELESAI")
