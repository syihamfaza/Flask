import time
import os
import pikepdf
from pathlib import Path

download_dir = str(Path.home() / "Downloads")


def rename_latest_file(extension, new_name, timeout=30):
    print(f"⏳ Menunggu file {extension} diunduh...")
    start_time = time.time()
    file_ready = False
    downloaded_file = None

    while time.time() - start_time < timeout:
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith(extension)]
        crdownload_files = [f for f in os.listdir(download_dir) if f.endswith(".crdownload")]

        if crdownload_files:
            time.sleep(1)  # masih mendownload, tunggu
            continue

        if files:
            # Ambil file terakhir berdasarkan waktu modifikasi
            downloaded_file = max(files, key=os.path.getctime)
            if os.path.getsize(downloaded_file) > 1024:  # minimal 1KB untuk validasi
                file_ready = True
                break

        time.sleep(1)

    if not file_ready:
        print(f"❌ Gagal mengunduh file {extension} dalam {timeout} detik.")
        return

    new_path = os.path.join(download_dir, new_name)
    try:
        os.rename(downloaded_file, new_path)
        print(f"✅ File berhasil diunduh dan disimpan sebagai: {new_name}")
    except Exception as e:
        print(f"⚠️ Gagal mengganti nama file: {e}")


def wait_for_download_complete(folder, extension=".pdf", timeout=60):
    """
    Menunggu hingga file dengan ekstensi tertentu selesai diunduh.
    Cek jika tidak ada file .crdownload dan file target sudah ada.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Cari file .crdownload → tanda masih mengunduh
        if any(f.endswith(".crdownload") for f in os.listdir(folder)):
            time.sleep(1)
            continue

        # Cari file target dengan ekstensi benar
        files = [f for f in os.listdir(folder) if f.endswith(extension)]
        if files:
            full_path = os.path.join(folder, max(files, key=lambda f: os.path.getctime(os.path.join(folder, f))))
            if os.path.getsize(full_path) > 0:
                print(f"✅ Download selesai: {full_path}")
                return full_path

        time.sleep(1)

    print("❌ Timeout: File belum selesai diunduh.")
    return None

def unlock_pdf(input_path, output_path, password=''):
    try:
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
        print(f"✅ PDF berhasil di-unlock: {output_path}")
    except pikepdf.PasswordError:
        print(f"❌ Gagal buka PDF, password salah atau tidak diketahui: {input_path}")
    except Exception as e:
        print(f"❌ Error unlock PDF: {e}")